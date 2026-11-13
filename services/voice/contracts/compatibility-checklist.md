# voice.v1 real-peer compatibility checklist

Baseline: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

| Check | Fixture mode | Real-peers mode |
| --- | --- | --- |
| Request has exactly one of `audio_uri` / `text` | covered | covered |
| `consent=false` rejected | covered | covered |
| Original input preserved in `original_text` | covered | covered |
| Amount/negation ambiguity flagged; no financial authority | covered | covered |
| Provider outage → explicit failure (no silent fixture fallback) | covered via injected fault | must remain visible |
| Malformed provider JSON → explicit failure | covered | covered |
| Secrets never in responses, fixtures, or logs | covered | covered |
| Retention mode `none` stores nothing | covered | covered |
| Optional TTS labeled fixture/live | covered | unverified until live run |

Assembly with a live Sarvam account is owner-run and unverified in this component PR.
