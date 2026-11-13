from sentinel_api.adapters.peers.fixture_clients import FixtureWorkflowClient

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")


def make(behavior: str = "valid") -> FixtureWorkflowClient:
    return FixtureWorkflowClient(behavior=behavior)  # type: ignore[arg-type]
