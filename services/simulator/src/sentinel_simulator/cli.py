from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from sentinel_simulator.domain.journeys import FAULT_SCHEDULES, JOURNEY_PACKS, SANDBOX_TENANT_ID


def _admin_post(base_url: str, path: str, token: str, body: dict | None = None) -> dict:
    payload = json.dumps(body or {}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the synthetic payment-provider HTTP API")
    serve.add_argument("--host", default=os.environ.get("SIMULATOR_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("SIMULATOR_PORT", "8094")))

    demo_reset = sub.add_parser(
        "demo-reset",
        help="Reset running sandbox store to journey seed packs (tenant-demo only)",
    )
    demo_reset.add_argument(
        "--base-url",
        default=os.environ.get("SIMULATOR_BASE_URL", "http://127.0.0.1:8094"),
    )
    demo_reset.add_argument(
        "--token",
        default=os.environ.get("SIMULATOR_TOKEN_SANDBOX_ADMIN", "tok-sandbox-admin-demo"),
    )
    demo_reset.add_argument(
        "--tenant",
        default=os.environ.get("SIMULATOR_TENANT_ID", SANDBOX_TENANT_ID),
        help="Must be tenant-demo; other tenants are refused",
    )

    seed = sub.add_parser("seed", help="Load a named journey seed pack on the running server")
    seed.add_argument(
        "pack",
        choices=[*JOURNEY_PACKS, "all"],
        help="Journey pack name, or all (demo-reset)",
    )
    seed.add_argument(
        "--base-url",
        default=os.environ.get("SIMULATOR_BASE_URL", "http://127.0.0.1:8094"),
    )
    seed.add_argument(
        "--token",
        default=os.environ.get("SIMULATOR_TOKEN_SANDBOX_ADMIN", "tok-sandbox-admin-demo"),
    )

    fault = sub.add_parser("fault", help="Apply a named fault schedule on the running server")
    fault.add_argument("schedule", choices=sorted(FAULT_SCHEDULES))
    fault.add_argument(
        "--base-url",
        default=os.environ.get("SIMULATOR_BASE_URL", "http://127.0.0.1:8094"),
    )
    fault.add_argument(
        "--token",
        default=os.environ.get("SIMULATOR_TOKEN_SANDBOX_ADMIN", "tok-sandbox-admin-demo"),
    )

    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        from sentinel_simulator.composition.app import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")
        return 0

    if args.command == "demo-reset":
        if args.tenant != SANDBOX_TENANT_ID:
            print(
                f"demo-reset refuses tenant {args.tenant!r}; only {SANDBOX_TENANT_ID!r}",
                file=sys.stderr,
            )
            return 2
        # Server also requires SIMULATOR_SANDBOX=true and principal.tenant_id=tenant-demo.
        result = _admin_post(args.base_url, "/v1/admin/demo-reset", args.token)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "seed":
        if args.pack == "all":
            result = _admin_post(args.base_url, "/v1/admin/demo-reset", args.token)
        else:
            result = _admin_post(args.base_url, f"/v1/admin/seeds/{args.pack}", args.token)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "fault":
        result = _admin_post(
            args.base_url, f"/v1/admin/faults/schedules/{args.schedule}", args.token
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
