"""Test-only deterministic embedder. Never wired at runtime.

Maps words onto a few hand-picked concept axes (so paraphrases like "charged twice"
and "duplicate payment" land close together) plus hashed axes for everything else.
"""

from __future__ import annotations

import math
import re
import zlib
from collections.abc import Sequence

CONCEPTS = {
    "billing": {"charged", "charge", "charges", "billed", "bill", "payment", "paid", "debit"},
    "repeat": {"twice", "duplicate", "double", "two", "again", "repeated"},
    "shipping": {"shipping", "delivery", "courier", "parcel", "delayed"},
    "access": {"password", "login", "reset", "account"},
}
_AXES = list(CONCEPTS)
HASHED_AXES = 28


class FakeEmbedder:
    def __init__(self, model_name: str = "test/fake-embedder", dimension: int = 32) -> None:
        assert dimension == len(_AXES) + HASHED_AXES
        self.model_name = model_name
        self.dimension = dimension

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for word in re.findall(r"[a-z]+", text.lower()):
            hit = [i for i, axis in enumerate(_AXES) if word in CONCEPTS[axis]]
            for i in hit:
                vector[i] += 1.0
            if not hit:
                vector[len(_AXES) + zlib.crc32(word.encode()) % HASHED_AXES] += 0.3
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]
