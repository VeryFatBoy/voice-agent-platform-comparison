#!/usr/bin/env python3
"""Export only the three final comparison agents and their linked VoiceTest data.

The source DuckDB database is opened read-only. The script exports:
  * the three final comparison agents (Vapi, Retell, LiveKit)
  * their three runs
  * the 24 result records linked to those runs
  * the 24 test cases referenced by those results
  * the schema-version history

The empty calls table is intentionally omitted. Workstation-specific source
paths and user IDs are removed from the exported agent/run rows.

Usage:
    python export_voicetest_db_to_csv.py [database_path] [output_directory]

Defaults:
    ~/.voicetest/data.duckdb
    ./voicetest-final-comparison-csv

Requires: duckdb Python package.
"""

from pathlib import Path
import argparse
import csv
import duckdb

TARGET_AGENT_NAMES = ("Riley", "Retell - Riley", "LiveKit - Riley")


def qi(identifier: str) -> str:
    """Quote an SQL identifier discovered from DuckDB metadata."""
    return '"' + identifier.replace('"', '""') + '"'


def write_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "database", nargs="?", type=Path,
        default=Path.home() / ".voicetest" / "data.duckdb",
    )
    parser.add_argument(
        "output_directory", nargs="?", type=Path,
        default=Path("voicetest-final-comparison-csv"),
    )
    args = parser.parse_args()
    db_path = args.database.expanduser().resolve()
    out_dir = args.output_directory.expanduser().resolve()
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        print("DuckDB Python version:", duckdb.__version__)
        print("Database:", db_path)
        print("Output directory:", out_dir)

        # Discover actual table names and columns; fail clearly if schema differs.
        tables = con.execute("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        """).fetchall()
        available = {(s, t): typ for s, t, typ in tables}
        required = [("main", name) for name in
                    ("agents", "runs", "results", "test_cases", "schema_version")]
        missing = [f"{s}.{t}" for s, t in required if (s, t) not in available]
        if missing:
            raise RuntimeError("Expected VoiceTest tables not found: " + ", ".join(missing))

        agents = con.execute("""
            SELECT * FROM main.agents
            WHERE name IN (?, ?, ?)
            ORDER BY CASE name
                WHEN 'Riley' THEN 1
                WHEN 'Retell - Riley' THEN 2
                WHEN 'LiveKit - Riley' THEN 3
                ELSE 4 END
        """, list(TARGET_AGENT_NAMES)).fetchall()
        agent_columns = [d[0] for d in con.description]
        if len(agents) != 3:
            raise RuntimeError(
                f"Expected exactly 3 target agents {TARGET_AGENT_NAMES}; found {len(agents)}. "
                "Review agent names before exporting; do not silently broaden the filter."
            )
        agent_index = {name: agent_columns.index(name) for name in agent_columns}
        agent_ids = [row[agent_index["id"]] for row in agents]
        agent_names = [row[agent_index["name"]] for row in agents]

        runs = con.execute("""
            SELECT * FROM main.runs
            WHERE agent_id IN (SELECT id FROM main.agents WHERE name IN (?, ?, ?))
            ORDER BY started_at
        """, list(TARGET_AGENT_NAMES)).fetchall()
        run_columns = [d[0] for d in con.description]
        if len(runs) != 3:
            raise RuntimeError(f"Expected 3 final comparison runs; found {len(runs)}")
        run_id_idx = run_columns.index("id")
        run_ids = [row[run_id_idx] for row in runs]

        results = con.execute("""
            SELECT * FROM main.results
            WHERE run_id IN (SELECT id FROM main.runs
                WHERE agent_id IN (SELECT id FROM main.agents WHERE name IN (?, ?, ?)))
            ORDER BY created_at, id
        """, list(TARGET_AGENT_NAMES)).fetchall()
        result_columns = [d[0] for d in con.description]
        if len(results) != 24:
            raise RuntimeError(f"Expected 24 linked result records; found {len(results)}")
        test_case_ids = sorted({row[result_columns.index("test_case_id")] for row in results
                                if row[result_columns.index("test_case_id")] is not None})
        if len(test_case_ids) != 24:
            raise RuntimeError(f"Expected 24 referenced test cases; found {len(test_case_ids)}")

        # Parameter placeholders avoid interpolating data values into SQL.
        placeholders = ",".join("?" for _ in test_case_ids)
        test_cases = con.execute(
            f"SELECT * FROM main.test_cases WHERE id IN ({placeholders}) ORDER BY agent_id, name",
            test_case_ids,
        ).fetchall()
        test_columns = [d[0] for d in con.description]
        if len(test_cases) != 24:
            raise RuntimeError(f"Expected 24 linked test cases; found {len(test_cases)}")

        schema_rows = con.execute(
            "SELECT * FROM main.schema_version ORDER BY version"
        ).fetchall()
        schema_columns = [d[0] for d in con.description]

        # Drop account identifiers and local filesystem paths from the agent export.
        keep_agent_cols = [c for c in agent_columns if c not in {"user_id", "source_path"}]
        agent_rows = [tuple(row[agent_index[c]] for c in keep_agent_cols) for row in agents]
        keep_run_cols = [c for c in run_columns if c != "user_id"]
        run_rows = [tuple(row[run_columns.index(c)] for c in keep_run_cols) for row in runs]

        outputs = [
            ("main__agents.csv", keep_agent_cols, agent_rows),
            ("main__runs.csv", keep_run_cols, run_rows),
            ("main__results.csv", result_columns, results),
            ("main__test_cases.csv", test_columns, test_cases),
            ("main__schema_version.csv", schema_columns, schema_rows),
        ]
        manifest = []
        for filename, columns, rows in outputs:
            write_csv(out_dir / filename, columns, rows)
            table = filename.removeprefix("main__").removesuffix(".csv")
            manifest.append(("main", table, len(rows), filename))
            print(f"Exported main.{table}: {len(rows)} rows -> {filename}")

        with (out_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["schema", "table", "row_count", "file"])
            writer.writerows(manifest)
            writer.writerow(["main", "calls", 0, "OMITTED: source table was empty"])

        print("\nAgents:", ", ".join(agent_names))
        print("Runs:", len(runs), "| Results:", len(results), "| Test cases:", len(test_cases))
        print("Calls table: 0 rows; omitted from CSV files")
        print("Manifest:", out_dir / "manifest.csv")
    finally:
        con.close()


if __name__ == "__main__":
    main()
