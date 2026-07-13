"""Simulator registry — the plugin mechanism for the Lab Engine.

The engine resolves a simulator by ``Lab.simulator_key`` at runtime. Nothing
in the engine, services or routes imports a concrete simulator, so new lab
types are additive.

=== EXTENSION POINT ===
Register a new simulator in one of two ways:

    # 1. Decorator (preferred)
    @register_simulator
    class NmapSimulator(Simulator):
        key = "nmap"
        ...

    # 2. Explicit
    SimulatorRegistry.register(NmapSimulator)

Then import the module once in app/labs/simulators/__init__.py so the
registration executes. That's the whole plugin contract.
"""

from __future__ import annotations

from typing import Optional, Type

from app.labs.simulator_base import Simulator, SimulatorError


class SimulatorRegistry:
    """Maps simulator_key -> Simulator class. Populated at import time."""

    _registry: dict[str, Type[Simulator]] = {}

    @classmethod
    def register(cls, simulator_cls: Type[Simulator]) -> Type[Simulator]:
        """Add a simulator class to the registry (idempotent per key)."""
        key = getattr(simulator_cls, "key", "")
        if not key:
            raise SimulatorError(
                f"{simulator_cls.__name__} must define a non-empty `key`."
            )
        cls._registry[key] = simulator_cls
        return simulator_cls

    @classmethod
    def get(cls, key: str) -> Optional[Simulator]:
        """Instantiate the simulator for a key, or None if unregistered."""
        simulator_cls = cls._registry.get(key or "")
        if simulator_cls is None:
            return None
        return simulator_cls()

    @classmethod
    def require(cls, key: str) -> Simulator:
        """Like get(), but raises when the key is unknown."""
        simulator = cls.get(key)
        if simulator is None:
            raise SimulatorError(f"No simulator registered for key '{key}'.")
        return simulator

    @classmethod
    def keys(cls) -> list[str]:
        """All registered simulator keys (for admin/seed validation)."""
        return sorted(cls._registry)

    @classmethod
    def is_registered(cls, key: str) -> bool:
        return (key or "") in cls._registry


def register_simulator(simulator_cls: Type[Simulator]) -> Type[Simulator]:
    """Class decorator — registers a simulator plugin."""
    return SimulatorRegistry.register(simulator_cls)
