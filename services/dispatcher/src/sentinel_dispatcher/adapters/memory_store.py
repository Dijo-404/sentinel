"""In-process worker store for unit fixtures that do not need durability."""

from __future__ import annotations

from sentinel_dispatcher.domain.types import DispatchJob


class MemoryWorkerStore:
    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], DispatchJob] = {}

    def save(self, job: DispatchJob) -> None:
        self._jobs[(job.tenant_id, job.action_id)] = job

    def get(self, tenant_id: str, action_id: str) -> DispatchJob | None:
        return self._jobs.get((tenant_id, action_id))

    def list_incomplete(self, tenant_id: str) -> list[DispatchJob]:
        return [
            job
            for (tenant, _), job in self._jobs.items()
            if tenant == tenant_id and job.phase not in {"OUTCOME_REPORTED", "ESCALATED"}
        ]
