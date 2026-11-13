"""Standalone voice.v1 client example against an in-process fixture app.

Does not touch apps/web. Secrets never enter a browser bundle.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_voice.bootstrap import build_app
from sentinel_voice.client import VoiceClient


def main() -> None:
    app = build_app(mode="fixture")
    with TestClient(app) as http:
        client = VoiceClient(
            "http://testserver",
            token="voice-demo-token",
            client=http,
        )
        caps = client.capabilities()
        print(f"capabilities={caps}")
        tamil = client.transcribe(
            language="ta-IN",
            consent=True,
            text="எனக்கு ரூபாய் 1500 refund வேண்டாம், cancel பண்ணுங்க",
        )
        print(
            "tamil "
            f"ambiguous={tamil.ambiguous} "
            f"codes={list(tamil.reason_codes)} "
            f"original={tamil.original_text!r}"
        )
        spoken = client.speak(
            language="en-IN",
            text="Your case is waiting for supervisor approval",
            consent=True,
        )
        print(f"speak uri={spoken.audio_uri} mode={spoken.evidence_mode}")


if __name__ == "__main__":
    main()
