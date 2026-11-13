"""Synthetic payment-provider.v1 simulator with deterministic fault controls."""

from .composition.app import create_app

__all__ = ["create_app"]
