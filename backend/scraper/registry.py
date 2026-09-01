"""
SIH26056 — Source registry.

Maps source names to factories so the pipeline can resolve ``ENABLED_SOURCES``
without importing any particular adapter. Adding a source means registering it
here; the index engine is untouched.

Disabled sources stay registered on purpose. A registry that lists a source as
``enabled=False`` with a stated reason is documentation — it records that the source
was assessed and why it is not used. Deleting the adapter instead would leave the
question unanswered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from loguru import logger

from provenance import SourceType
from scraper.base import FareSource, SourceCapability


SourceFactory = Callable[..., FareSource]


@dataclass(frozen=True)
class Registration:
    name: str
    factory: SourceFactory
    describe: Callable[[], SourceCapability]


class SourceRegistry:
    """Name -> factory registry with capability introspection."""

    def __init__(self):
        self._registrations: dict[str, Registration] = {}

    def register(
        self,
        name: str,
        factory: SourceFactory,
        describe: Callable[[], SourceCapability],
    ) -> None:
        key = name.strip().lower()
        if key in self._registrations:
            raise ValueError(f"Source {key!r} is already registered")
        self._registrations[key] = Registration(name=key, factory=factory, describe=describe)

    def names(self) -> list[str]:
        return sorted(self._registrations)

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._registrations

    def capability(self, name: str) -> SourceCapability:
        key = name.strip().lower()
        if key not in self._registrations:
            raise KeyError(f"Unknown source {name!r}. Registered: {self.names()}")
        return self._registrations[key].describe()

    def capabilities(self) -> list[SourceCapability]:
        return [reg.describe() for _, reg in sorted(self._registrations.items())]

    def create(self, name: str, **kwargs: Any) -> FareSource:
        key = name.strip().lower()
        if key not in self._registrations:
            raise KeyError(f"Unknown source {name!r}. Registered: {self.names()}")
        return self._registrations[key].factory(**kwargs)

    def resolve(
        self,
        requested: list[str],
        source_type: Optional[SourceType] = None,
        **kwargs: Any,
    ) -> tuple[list[FareSource], list[dict[str, str]]]:
        """
        Instantiate the requested sources.

        Returns ``(sources, skipped)`` where each ``skipped`` entry carries the
        reason. Unknown names, wrong-type names, and disabled adapters are reported
        rather than silently ignored, so a misconfigured ``ENABLED_SOURCES`` is
        visible instead of quietly yielding an empty collection run.
        """
        sources: list[FareSource] = []
        skipped: list[dict[str, str]] = []

        for name in requested:
            key = name.strip().lower()
            if not key:
                continue
            if key not in self._registrations:
                skipped.append({
                    "source": key,
                    "reason": f"not registered (available: {', '.join(self.names())})",
                    "reason_type": "unknown_source",
                })
                logger.warning(f"ENABLED_SOURCES lists unknown source {key!r}")
                continue

            capability = self._registrations[key].describe()

            if source_type is not None and capability.source_type is not source_type:
                skipped.append({
                    "source": key,
                    "reason": (
                        f"source provides {capability.source_type.value} data but the "
                        f"pipeline is running in a mode that requires "
                        f"{source_type.value} data"
                    ),
                    "reason_type": "mode_mismatch",
                })
                continue

            if not capability.enabled:
                skipped.append({
                    "source": key,
                    "reason": capability.disabled_reason or "disabled",
                    "reason_type": "source_disabled",
                })
                logger.info(
                    f"Source {key!r} is disabled: {capability.disabled_reason}"
                )
                continue

            sources.append(self._registrations[key].factory(**kwargs))

        return sources, skipped


# ── module-level registry, populated on import of scraper.sources ──

registry = SourceRegistry()


def get_registry() -> SourceRegistry:
    """Registry accessor that guarantees the built-in adapters are registered."""
    import scraper.sources  # noqa: F401  (import side effect: registration)

    return registry
