"""Postgres checkpointer connection must stay open after bootstrap returns."""

from __future__ import annotations

import gc
from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver

from sentinel_workflow import bootstrap


class _FakeSaver:
    def __init__(self) -> None:
        self.closed = False

    def setup(self) -> None:
        pass


def test_checkpointer_context_not_closed_by_gc(monkeypatch) -> None:
    saver = _FakeSaver()

    @contextmanager
    def fake_from_conn_string(dsn: str):
        assert dsn.startswith("postgresql://")
        try:
            yield saver
        finally:
            saver.closed = True

    monkeypatch.setattr(PostgresSaver, "from_conn_string", staticmethod(fake_from_conn_string))
    monkeypatch.setattr(bootstrap, "_OPEN_CHECKPOINTER_CONTEXTS", [], raising=False)

    got = bootstrap._postgres_checkpointer("postgresql+psycopg://u:p@127.0.0.1:5432/workflow")
    gc.collect()

    assert got is saver
    assert saver.closed is False
