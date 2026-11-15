"""Local CPU embeddings via fastembed (ONNX Runtime). No external embedding API."""

from __future__ import annotations

from collections.abc import Sequence

from ..application.errors import PeerUnavailableError

DEFAULT_MODEL = "intfloat/multilingual-e5-small"

# multilingual-e5-small is not in fastembed's built-in catalog; the upstream HF repo
# ships an ONNX export, so register it as a custom mean-pooled, normalized model.
_CUSTOM_MODELS = {
    "intfloat/multilingual-e5-small": {"dim": 384, "model_file": "onnx/model.onnx"},
}


class FastEmbedEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL, cache_dir: str | None = None) -> None:
        try:
            from fastembed import TextEmbedding

            _register_custom(TextEmbedding, model_name)
            self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir or None)
            self.dimension = len(next(iter(self._model.embed(["probe"]))))
        except Exception as exc:  # any load/download/runtime failure must fail closed
            raise PeerUnavailableError(f"embedding model unavailable: {model_name}") from exc
        self.model_name = model_name
        # E5 models are trained with these role prefixes; other models take raw text.
        self._e5 = "e5" in model_name.lower()

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" if self._e5 else t for t in texts]
        return self._embed(prefixed)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([f"query: {text}" if self._e5 else text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return [vector.tolist() for vector in self._model.embed(texts)]
        except Exception as exc:
            raise PeerUnavailableError("embedding failed") from exc


def _register_custom(text_embedding, model_name: str) -> None:
    spec = _CUSTOM_MODELS.get(model_name)
    if spec is None:
        return
    if any(m["model"] == model_name for m in text_embedding.list_supported_models()):
        return
    from fastembed.common.model_description import ModelSource, PoolingType

    text_embedding.add_custom_model(
        model=model_name,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=model_name),
        dim=spec["dim"],
        model_file=spec["model_file"],
    )
