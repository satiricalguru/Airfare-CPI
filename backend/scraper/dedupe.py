"""
SIH26056 — Cross-source deduplication.

The same seat can surface through several sources: an airline's own site, a GDS,
and one or more OTAs. Counting it once per source would inflate the sample size and
over-weight whichever products happen to be widely distributed — the elementary
index is an unweighted geometric mean over products, so a product appearing three
times gets three times the influence.

Duplicate identity is :meth:`FareObservation.dedupe_fingerprint`: the same flight,
same product characteristics, same booking horizon, same collection day. Price is
deliberately excluded, because two sources quoting slightly different prices for the
same seat are still the same seat.

Which duplicate survives is decided by an explicit, deterministic rule
(:class:`DedupeStrategy`) rather than arrival order, so a collection run is
reproducible.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional

from loguru import logger

from scraper.base import FareObservation


class DedupeStrategy(str, Enum):
    """How to choose the surviving observation within a duplicate group."""

    # Prefer the source listed earliest in the configured priority order. Default:
    # source priority is an operator decision about which source is most reliable.
    SOURCE_PRIORITY = "source_priority"
    # Keep the lowest fare — the price a consumer could actually have paid.
    LOWEST_FARE = "lowest_fare"
    # Keep the most recently collected quote.
    MOST_RECENT = "most_recent"


@dataclass
class DedupeResult:
    kept: list[FareObservation]
    removed: list[FareObservation]
    strategy: DedupeStrategy
    # fingerprint -> the source names that offered it
    duplicate_groups: dict[str, list[str]] = field(default_factory=dict)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def duplicate_group_count(self) -> int:
        return len(self.duplicate_groups)

    def summary(self) -> dict[str, Any]:
        return {
            "input_count": len(self.kept) + len(self.removed),
            "kept": len(self.kept),
            "removed_as_duplicates": self.removed_count,
            "duplicate_groups": self.duplicate_group_count,
            "strategy": self.strategy.value,
            # Max spread within a duplicate group is a useful signal: a large spread
            # suggests the fingerprint is matching products that are not identical.
            "max_intra_group_price_spread_pct": self._max_spread_pct(),
        }

    def _max_spread_pct(self) -> Optional[float]:
        return self._max_spread

    _max_spread: Optional[float] = None


def deduplicate(
    observations: Iterable[FareObservation],
    strategy: DedupeStrategy = DedupeStrategy.SOURCE_PRIORITY,
    source_priority: Optional[list[str]] = None,
) -> DedupeResult:
    """
    Collapse duplicate products to one observation each.

    ``source_priority`` orders sources for :attr:`DedupeStrategy.SOURCE_PRIORITY`;
    sources absent from the list sort last. Ties break on source name then fare so
    the outcome is fully deterministic.
    """
    priority_index = {
        name.strip().lower(): i for i, name in enumerate(source_priority or [])
    }

    groups: dict[str, list[FareObservation]] = defaultdict(list)
    for obs in observations:
        groups[obs.dedupe_fingerprint()].append(obs)

    def sort_key(obs: FareObservation):
        source = (obs.provenance.source_name or "").lower()
        rank = priority_index.get(source, len(priority_index))
        if strategy is DedupeStrategy.LOWEST_FARE:
            return (obs.fare_total, rank, source)
        if strategy is DedupeStrategy.MOST_RECENT:
            return (-obs.collection_datetime.timestamp(), rank, source, obs.fare_total)
        return (rank, source, obs.fare_total)

    kept: list[FareObservation] = []
    removed: list[FareObservation] = []
    duplicate_groups: dict[str, list[str]] = {}
    max_spread: Optional[float] = None

    for fingerprint, members in groups.items():
        if len(members) == 1:
            kept.append(members[0])
            continue

        ordered = sorted(members, key=sort_key)
        kept.append(ordered[0])
        removed.extend(ordered[1:])
        duplicate_groups[fingerprint] = sorted(
            {(m.provenance.source_name or "unknown") for m in members}
        )

        fares = [m.fare_total for m in members]
        low, high = min(fares), max(fares)
        if low > 0:
            spread = (high - low) / low * 100
            max_spread = spread if max_spread is None else max(max_spread, spread)

    if removed:
        logger.info(
            f"Deduplication ({strategy.value}): removed {len(removed)} duplicate "
            f"observation(s) across {len(duplicate_groups)} product group(s); "
            f"kept {len(kept)}"
        )

    result = DedupeResult(
        kept=kept,
        removed=removed,
        strategy=strategy,
        duplicate_groups=duplicate_groups,
    )
    result._max_spread = round(max_spread, 2) if max_spread is not None else None
    return result
