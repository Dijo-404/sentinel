from sentinel_api.adapters.peers.fixture_clients import FixtureLedgerClient

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")


def make(behavior: str = "valid") -> FixtureLedgerClient:
    return FixtureLedgerClient(behavior=behavior)  # type: ignore[arg-type]
