"""Environment-configured, redacted CLI for the private synthetic demonstration."""

import argparse
import json
import os
import sys
from dataclasses import asdict

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from .contracts import CONTRACT_VERSION, PORT, ConfigurationError, ServiceSchema
from .demo import inspect_demo, migrate_demo, reset_demo, seed_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Private PostgreSQL synthetic persistence demo")
    parser.add_argument("operation", choices=("migrate", "seed", "reset", "inspect"))
    args = parser.parse_args()
    engine = None
    try:
        if os.environ.get("PERSISTENCE_CONTRACT_VERSION", CONTRACT_VERSION) != CONTRACT_VERSION:
            raise ConfigurationError("Unsupported required contract version")
        url = make_url(os.environ["DATABASE_URL"])
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ConfigurationError("Use a postgresql+psycopg URL with explicit database")
        service = ServiceSchema(
            os.environ["PERSISTENCE_SCHEMA"], os.environ["PERSISTENCE_RUNTIME_ROLE"]
        )
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
        if args.operation == "inspect":
            report = inspect_demo(engine, service, os.environ["PERSISTENCE_TENANT_ID"])
            print(json.dumps(asdict(report), sort_keys=True))
        else:
            operation = {"migrate": migrate_demo, "seed": seed_demo, "reset": reset_demo}[
                args.operation
            ]
            operation(engine, service, environment=os.environ.get("PERSISTENCE_ENVIRONMENT", ""))
            print(
                json.dumps(
                    {
                        "contract_version": CONTRACT_VERSION,
                        "port": PORT,
                        "operation": args.operation,
                        "evidence_mode": "real-postgresql/synthetic-records",
                    },
                    sort_keys=True,
                )
            )
        return 0
    except (ConfigurationError, KeyError, ArgumentError, ValueError):
        print(
            "Invalid or unsafe persistence configuration; check required environment fields.",
            file=sys.stderr,
        )
        return 2
    except SQLAlchemyError:
        # Driver exception strings can include credentials, identifiers or SQL parameters.
        print(
            "PostgreSQL database operation failed; no fixture fallback was used.", file=sys.stderr
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
