#!/usr/bin/env python3
"""
Read-only credential scan for a DuckDB database.

Usage:
    python -m pip install -r tools/requirements.txt
    python scan_duckdb_credentials.py /path/to/data.duckdb

The script does not modify the database and does not print matched secret values.
It reports table, column, row number, and the category of each possible finding.
Review findings manually: IDs, placeholders, and test fixtures can trigger
false positives.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("Missing dependency. Install it with: python -m pip install -r tools/requirements.txt")
    sys.exit(2)


PATTERNS = [
    ("private-key material", re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I)),
    ("authorization bearer token", re.compile(
        r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I)),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("Vapi-style API key", re.compile(
        r"\b(?:vapi|retell)[-_ ]?(?:api[-_ ]?)?key\s*[:=]\s*['\"]?[A-Za-z0-9._-]{16,}",
        re.I)),
    ("credential assignment", re.compile(
        r"\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
        r"password|passwd|secret)\b\s*[:=]\s*['\"]?[^'\"\s,;]{8,}", re.I)),
    ("URL with embedded credentials", re.compile(
        r"\bhttps?://[^/\s:@]+:[^/\s@]+@", re.I)),
]

SENSITIVE_COLUMN = re.compile(
    r"(api.?key|access.?token|refresh.?token|client.?secret|password|passwd|"
    r"credential|private.?key|authorization|auth.?header)", re.I
)

def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", help="Path to the DuckDB database file")
    parser.add_argument("--max-findings", type=int, default=200,
                        help="Maximum findings to print (default: 200)")
    args = parser.parse_args()

    db_path = Path(args.database).expanduser().resolve()
    if not db_path.is_file():
        print(f"Database file not found: {db_path}")
        return 2

    # read_only=True prevents accidental changes to the source database.
    con = duckdb.connect(str(db_path), read_only=True)
    findings = []
    scanned_cells = 0
    scanned_tables = 0
    table_inventory = []

    try:
        table_rows = con.execute("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
        """).fetchall()

        for schema, table, table_type in table_rows:
            scanned_tables += 1
            qualified = f"{quote_ident(schema)}.{quote_ident(table)}"
            columns = con.execute(f"DESCRIBE SELECT * FROM {qualified}").fetchall()
            table_inventory.append((schema, table, table_type, len(columns)))

            # Include text-like columns; flag sensitive column names even if empty.
            text_columns = []
            for col in columns:
                col_name, col_type = col[0], str(col[1]).upper()
                if SENSITIVE_COLUMN.search(col_name):
                    findings.append((schema, table, col_name, "sensitive column name"))
                if any(t in col_type for t in
                       ("VARCHAR", "CHAR", "STRING", "TEXT", "JSON", "ENUM")):
                    text_columns.append(col_name)

            if not text_columns:
                continue

            select_cols = ", ".join(quote_ident(c) for c in text_columns)
            rows = con.execute(f"SELECT {select_cols} FROM {qualified}").fetchall()

            for row_num, row in enumerate(rows, start=1):
                for col_name, value in zip(text_columns, row):
                    if value is None:
                        continue
                    scanned_cells += 1
                    value_text = str(value)
                    for label, pattern in PATTERNS:
                        if pattern.search(value_text):
                            findings.append((schema, table, col_name,
                                             f"{label} (row {row_num})"))
                            break

    finally:
        con.close()

    print(f"\nDatabase: {db_path.name}")
    print(f"Tables/views scanned: {scanned_tables}")
    print(f"Text cells scanned: {scanned_cells}")
    print("\nTable inventory:")
    for schema, table, kind, ncols in table_inventory:
        print(f"  {schema}.{table} [{kind}; {ncols} columns]")

    print("\nPotential credential findings:")
    if not findings:
        print("  No matches found by the configured checks.")
    else:
        for schema, table, column, reason in findings[:args.max_findings]:
            print(f"  {schema}.{table}.{column}: {reason}")
        if len(findings) > args.max_findings:
            print(f"  ... {len(findings) - args.max_findings} additional findings omitted.")

    print("\nIMPORTANT:")
    print("- No matches does NOT prove the database contains no credentials.")
    print("- Review suspicious columns and any flagged rows in your local environment.")
    print("- Also check for personal data or other confidential information before sharing.")
    print("- This scan does not upload or transmit database contents.")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
