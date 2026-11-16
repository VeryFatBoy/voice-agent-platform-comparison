# Voice Agent Platform Comparison: Vapi, Retell AI and LiveKit

This repository holds the technical report and evidence behind the DZone article [Vapi vs. Retell AI vs. LiveKit: Architecture, Latency, Pricing and Developer Experience](https://dzone.com/articles/vapi-vs-retell-ai-vs-livekit-architecture-latency).

## Read this first

We ran eight appointment scenarios once against prompts and graphs imported from each platform into the open-source VoiceTest tool. It's a prompt and graph simulation, not a comparison of native vendor runtimes. The same model played agent, simulator and judge, and our transcript audit found judge errors and unsupported agent claims. The recorded pass counts aren't a reliable measure of agent quality and shouldn't be used to rank platforms. The report explains why.

## What's inside

- `report/`: the full technical report as Markdown and PDF
- `evidence/`: the test suite, results, transcripts, vendor configuration exports, the LiveKit source and the imported graphs
- `tools/`: the scripts we used to inspect and export the VoiceTest database

## Reproduce the export

The scripts in `tools/` need one pinned dependency:

```
python -m pip install -r tools/requirements.txt
```

We didn't include the original VoiceTest database or a dependency lockfile. The report's appendices explain what was and wasn't retained.

## Licenses

The report, evidence and data are licensed under CC BY 4.0, and the scripts in `tools/` are licensed under MIT. See `LICENSE` and `tools/LICENSE`.
