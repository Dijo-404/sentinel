"""Task-local typed snapshot of the persistence-kit.v1 library boundary."""

import re
from dataclasses import dataclass
from typing import Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "persistence-kit.v1"


class ConfigurationError(ValueError):
    """Unsafe scope, role, or demo configuration; contains no connection secrets."""


def identifier(value: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value)
        or value.startswith("pg_")
        or value in {"public", "information_schema", "postgres"}
    ):
        raise ConfigurationError("Use a private lowercase PostgreSQL identifier (1–63 bytes)")
    return value


@dataclass(frozen=True)
class ServiceSchema:
    """One service's provisioned schema and unprivileged runtime login."""

    schema: str
    runtime_role: str

    def __post_init__(self) -> None:
        identifier(self.schema)
        identifier(self.runtime_role)
        if self.schema == self.runtime_role:
            raise ConfigurationError("Schema and runtime role must be distinct")


@dataclass(frozen=True)
class CheckReport:
    contract_version: Literal["sentinel.task-contracts.v1"]
    port: Literal["persistence-kit.v1"]
    evidence_mode: Literal["real-postgresql/synthetic-records"]
    schema: str
    migration_revision: str
    tenant_records: int
