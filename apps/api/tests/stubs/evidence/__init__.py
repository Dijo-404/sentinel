from sentinel_api.adapters.peers.fixture_clients import FixtureEvidenceClient

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")


def make(behavior: str = "valid") -> FixtureEvidenceClient:
    return FixtureEvidenceClient(behavior=behavior)  # type: ignore[arg-type]
