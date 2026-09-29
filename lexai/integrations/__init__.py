"""Integration layer for LEXAI.

Integrations (Gmail, Calendar, ...) are declared in integrations.yaml and
registered here. v0.1 ships only the contracts and the registry; concrete
integrations plug in later without changing the core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


class Integration(ABC):
    """Base class for every LEXAI integration.

    A concrete integration subclasses this, declares `name`, and is
    registered with `get_registry().register(MyIntegration)`. The core
    never imports integrations directly; everything goes through the
    registry so the brain can be taught to use them later.
    """

    #: Unique short name, e.g. "gmail". Must be set by subclasses.
    name: str = ""
    #: Human-readable description used in /status and future tool schemas.
    description: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config: Dict[str, Any] = config or {}

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("name"):
            raise TypeError(f"Integration subclass {cls.__name__} must define a non-empty 'name'")

    @abstractmethod
    def setup(self) -> None:
        """Prepare the integration (validate config, connect, etc.)."""

    @abstractmethod
    def teardown(self) -> None:
        """Release anything the integration held (sessions, tokens)."""

    def status(self) -> str:
        return f"{self.name}: ready"


@dataclass
class IntegrationRegistry:
    """Central registry of available integrations.

    Starts empty by design; integrations register themselves when LEXAI
    activates them based on integrations.yaml.
    """

    _classes: Dict[str, Type[Integration]] = field(default_factory=dict)
    _instances: Dict[str, Integration] = field(default_factory=dict)
    _config: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def register(self, integration_cls: Type[Integration]) -> Type[Integration]:
        name = integration_cls.name
        if not name:
            raise ValueError("Integration must define a non-empty 'name'")
        if name in self._classes:
            raise ValueError(f"Integration '{name}' is already registered")
        self._classes[name] = integration_cls
        return integration_cls

    def unregister(self, name: str) -> None:
        self._classes.pop(name, None)
        self._instances.pop(name, None)

    def is_registered(self, name: str) -> bool:
        return name in self._classes

    def declare(self, name: str, config: Dict[str, Any]) -> None:
        """Record a config entry from integrations.yaml for `name`."""
        self._config[name] = config or {}

    def activate(self, name: str) -> Integration:
        """Instantiate a registered integration and run its setup()."""
        if name in self._instances:
            return self._instances[name]
        if name not in self._classes:
            raise KeyError(f"No integration registered under '{name}'")
        instance = self._classes[name](config=self._config.get(name))
        instance.setup()
        self._instances[name] = instance
        return instance

    def get(self, name: str) -> Optional[Integration]:
        return self._instances.get(name)

    def active_names(self) -> List[str]:
        return sorted(self._instances)

    def registered_names(self) -> List[str]:
        return sorted(self._classes)

    def declared_names(self) -> List[str]:
        return sorted(self._config)


_registry: Optional[IntegrationRegistry] = None


def get_registry() -> IntegrationRegistry:
    """Process-wide registry accessor."""
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
    return _registry


def reset_registry() -> IntegrationRegistry:
    """Replace the global registry (used by tests and reloads)."""
    global _registry
    _registry = IntegrationRegistry()
    return _registry