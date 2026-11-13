"""In-memory SLA policy/task store for standalone fixture runs."""

from __future__ import annotations

from sentinel_merchant_sla.contracts import SlaPolicy, SlaTask


class MemorySlaStore:
    def __init__(self) -> None:
        self._policies: dict[str, SlaPolicy] = {}
        self._tasks: dict[str, SlaTask] = {}
        self._counters: dict[str, int] = {}

    def put_policy(self, policy: SlaPolicy) -> SlaPolicy:
        self._policies[policy.policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> SlaPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self, *, tenant_id: str, merchant_ref: str) -> list[SlaPolicy]:
        return [
            p
            for p in self._policies.values()
            if p.tenant_id == tenant_id and p.merchant_ref == merchant_ref
        ]

    def put_task(self, task: SlaTask) -> SlaTask:
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> SlaTask | None:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        *,
        tenant_id: str,
        merchant_ref: str | None = None,
        case_id: str | None = None,
    ) -> list[SlaTask]:
        out: list[SlaTask] = []
        for task in self._tasks.values():
            if task.tenant_id is not None and task.tenant_id != tenant_id:
                continue
            if merchant_ref is not None and task.merchant_ref != merchant_ref:
                continue
            if case_id is not None and task.case_id != case_id:
                continue
            out.append(task)
        return out

    def next_id(self, prefix: str) -> str:
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return f"{prefix}-{n}"
