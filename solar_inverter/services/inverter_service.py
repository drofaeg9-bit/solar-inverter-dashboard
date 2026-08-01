"""Stable public facade for the split inverter service implementation."""

from . import inverter_service_runtime as _runtime

__all__ = [name for name in dir(_runtime) if not name.startswith("_")]


def __getattr__(name: str):
    """Forward public attributes, including mutable runtime state."""
    return getattr(_runtime, name)
