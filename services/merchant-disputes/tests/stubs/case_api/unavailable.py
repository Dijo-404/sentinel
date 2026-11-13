"""Case: case-api unavailable."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureCaseApi

PEER = FixtureCaseApi(behavior="unavailable")
