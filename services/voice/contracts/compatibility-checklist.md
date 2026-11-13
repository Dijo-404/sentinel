# voice.v1 real-peer compatibility checklist

Baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

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
