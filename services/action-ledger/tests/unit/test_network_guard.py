"""ReservationNetworkGuard is request-scoped via contextvars."""

from __future__ import annotations

import concurrent.futures
import time

from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.domain.errors import ConflictError


def test_guard_trips_when_network_noted_inside_begin():
    guard = ReservationNetworkGuard()
    with guard.begin_guard():
        guard.note_network()
        try:
            guard.assert_idle()
            raise AssertionError("expected NETWORK_IN_TX")
        except ConflictError as exc:
            assert exc.code == "NETWORK_IN_TX"


def test_sibling_instances_share_context_state():
    """Peers may hold a different instance; contextvars still couple them."""
    a = ReservationNetworkGuard()
    b = ReservationNetworkGuard()
    with a.begin_guard():
        b.note_network()
        try:
            a.assert_idle()
            raise AssertionError("expected NETWORK_IN_TX")
        except ConflictError as exc:
            assert exc.code == "NETWORK_IN_TX"


def test_concurrent_guards_do_not_cross_contaminate():
    """Threadpool requests must not share active/calls counters."""
    guard = ReservationNetworkGuard()
    errors: list[str] = []

    def worker(note: bool) -> None:
        with guard.begin_guard():
            time.sleep(0.02)
            if note:
                guard.note_network()
                try:
                    guard.assert_idle()
                except ConflictError as exc:
                    if exc.code != "NETWORK_IN_TX":
                        errors.append(f"wrong code {exc.code}")
                else:
                    errors.append("expected NETWORK_IN_TX")
            else:
                try:
                    guard.assert_idle()
                except ConflictError:
                    errors.append("idle worker saw foreign network call")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker, i % 2 == 0) for i in range(16)]
        for fut in concurrent.futures.as_completed(futures):
            fut.result()

    assert errors == []
