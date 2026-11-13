from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the synthetic payment-provider HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8094)

    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        from sentinel_simulator.composition.app import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
