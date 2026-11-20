"""Plugin registries: sources, transforms, sinks and quality checks register themselves by name."""
from __future__ import annotations

from typing import Callable


class Registry:
    """A named collection of callables populated with a decorator.

        TRANSFORMS = Registry("transform")

        @TRANSFORMS.register("upper")
        def upper(records, ctx, columns): ...
    """

    def __init__(self, kind: str):
        """[provided]"""
        self.kind = kind
        self._items: dict[str, Callable] = {}

    def register(self, name: str) -> Callable[[Callable], Callable]:
        """[provided] Decorator registering `func` under `name`; duplicates raise ValueError."""
        def decorator(func: Callable) -> Callable:
            if name in self._items:
                raise ValueError(f"{self.kind} {name!r} is already registered")
            self._items[name] = func
            return func
        return decorator

    def get(self, name: str) -> Callable:
        """[provided] Look up by name; unknown names raise KeyError listing what is available."""
        try:
            return self._items[name]
        except KeyError:
            raise KeyError(f"unknown {self.kind} {name!r}; available: {sorted(self._items)}") from None

    def names(self) -> list[str]:
        """[provided] Sorted registered names."""
        return sorted(self._items)

    def __contains__(self, name: str) -> bool:
        """[provided]"""
        return name in self._items


SOURCES = Registry("source")
TRANSFORMS = Registry("transform")
CHECKS = Registry("quality check")
