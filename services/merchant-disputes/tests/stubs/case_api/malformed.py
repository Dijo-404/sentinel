"""Case: case-api returns malformed payload."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureCaseApi

PEER = FixtureCaseApi(behavior="malformed")
