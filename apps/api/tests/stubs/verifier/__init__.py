from sentinel_api.adapters.peers.fixture_clients import FixtureVerifierClient

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")


def make(behavior: str = "valid") -> FixtureVerifierClient:
    return FixtureVerifierClient(behavior=behavior)  # type: ignore[arg-type]
