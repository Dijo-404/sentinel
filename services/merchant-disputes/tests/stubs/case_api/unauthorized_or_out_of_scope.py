"""Case: case-api unauthorized or out of scope."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureCaseApi

PEER = FixtureCaseApi(behavior="unauthorized_or_out_of_scope")
