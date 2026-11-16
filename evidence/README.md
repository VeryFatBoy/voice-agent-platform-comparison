# Evidence

Everything here supports the report in `../report/`. Read the report's limitations first: the recorded pass counts aren't reliable measures of agent quality.

## File map

- `benchmark/voicetest_wellness_partners_test_suite.json`: the eight scenario definitions
- `benchmark/voicetest-final-results.json`: the 24 recorded result records
- `benchmark/voicetest-final-transcripts.json`: the 24 transcripts with evaluator criteria and reasoning
- `benchmark/duckdb-csv/`: filtered CSV export of the VoiceTest database, including `agents.csv` with the three imported agent graphs (`graph_json`)
- `livekit/agent.py`: the final LiveKit agent source
- `livekit/livekit-agent.json`: the graph VoiceTest imported from that source
- `retell/retell-agent-v1-snapshot.json`: a separate, unpublished Retell Version 1 snapshot. It isn't the Version 0 prompt export and isn't a VoiceTest graph.
- `vendor-configs/retell-v0-export.json`: the published Retell Version 0 dashboard export, including the exact prompt
- `vendor-configs/vapi-config.json`: the Vapi dashboard configuration export, including the full system prompt

## Redactions

Account identifiers were replaced with placeholders before publication:

| Placeholder | Where it appears |
| --- | --- |
| `REDACTED-VAPI-ORG-ID` | `vendor-configs/vapi-config.json` |
| `REDACTED-VAPI-ASSISTANT-ID` | `vendor-configs/vapi-config.json`, `benchmark/duckdb-csv/agents.csv` |
| `REDACTED-RETELL-LLM-ID` | `vendor-configs/retell-v0-export.json`, `retell/retell-agent-v1-snapshot.json`, `benchmark/duckdb-csv/agents.csv` |
| `REDACTED-RETELL-AGENT-ID` | `retell/retell-agent-v1-snapshot.json` |

VoiceTest's own run, result and agent UUIDs were kept. They aren't account identifiers.
