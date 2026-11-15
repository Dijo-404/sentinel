# README kit

Implemented in the root [README](../README.md). Paths in the copyable snippet below are relative to the repository root.

Both compressed videos are hosted in the [sandbox media prerelease](https://github.com/Dijo-404/sentinel/releases/tag/readme-media-2026-11-15), which is documentation media rather than a software release. Both posters in the root README and the snippet below open the uploaded YouTube videos.

All ten images/GIFs under `media/readme/` are committed. The videos and proof images describe the capture at `1a64a55` on 15 November 2026. See the [original fixture-check transcript](video/proof/core-check-1a64a55.txt) and [capture claims manifest](video/CLAIMS.md). Current setup and verification instructions remain in the root README.

```markdown
<p align="center"><img src="media/readme/banner.png" alt="Sentinel: every refund, from complaint to confirmed credit" width="100%"></p>

## Watch

|                                     Sentinel in 90 seconds                                      |                                       How Sentinel works                                        |
| :---------------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------------: |
| [![Sentinel in 90 seconds (1:29)](media/readme/poster-pitch.png)](https://youtu.be/U6B0VEkRMnc) | [![How Sentinel works (3:49)](media/readme/poster-explainer.png)](https://youtu.be/5mBIK9xCPPI) |

> Sandbox only. Every screen is the app running locally in fixture mode with synthetic data; payments go to a mock simulator.

## How a refund is authorized

![Six steps to authorize a refund](media/readme/flow-six-steps.png)

![The money path](media/readme/architecture.png)

## See it

|                     Case simulator                      |                                  Provider timeout                                  |                               Guardrails                                |
| :-----------------------------------------------------: | :--------------------------------------------------------------------------------: | :---------------------------------------------------------------------: |
| ![Case simulator](media/readme/demo-case-simulator.gif) | ![Provider timeout: reconcile, not resend](media/readme/demo-provider-timeout.gif) | ![Models propose, the server decides](media/readme/demo-guardrails.gif) |

## Proof

![make -C integration/core check, fixture mode, 1a64a55](media/readme/proof-assembly-check.png)

![Paytm staging observations, captured and redacted](media/readme/proof-paytm-staging.png)
```

Both posters open YouTube: [pitch (1:29)](https://youtu.be/U6B0VEkRMnc) and [explainer (3:49)](https://youtu.be/5mBIK9xCPPI). Downloadable MP4 backups remain available in the sandbox media prerelease.

## Files

| File                                 |             Size | Commit it?                              |
| :----------------------------------- | ---------------: | :-------------------------------------- |
| `media/sentinel-pitch-small.mp4`     |           7.3 MB | no: hosted as a release asset           |
| `media/sentinel-pitch.mp4`           |          14.2 MB | no (ignored)                            |
| `media/sentinel-explainer-small.mp4` |          18.0 MB | no (ignored): hosted as a release asset |
| `media/sentinel-explainer.mp4`       |          36.2 MB | no (ignored)                            |
| `media/readme/*`                     |  0.2–1.9 MB each | yes                                     |
| `media/sentinel-video-source.zip`    | source to re-cut | optional                                |

## Changing wording or timing later

The following commands require the optional original `media/video` source workspace and its captured screens/audio. That rebuildable workspace and source ZIP are not part of this documentation PR; a fresh checkout contains the finished README assets and capture evidence only.

```bash
cd media/video && npm ci
# edit timeline/pitch.json or timeline/explainer.json (scenes, cues and voiceover lines live there)
.venv/bin/python scripts/tts.py pitch && .venv/bin/python scripts/words.py pitch && .venv/bin/python scripts/audio.py pitch
node scripts/render.mjs pitch --force && .venv/bin/python scripts/check.py pitch
```

The Python environment is `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python kokoro-onnx faster-whisper soundfile numpy scipy pillow`. To re-shoot the screens against a real-peers stack: `BASE=http://localhost:3012 node scripts/capture.mjs`.
