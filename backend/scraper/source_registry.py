"""
SIH26056 — Source Access Registry reader and validator.

Loads and enforces the source governance registry defined in
`data/source_access_registry.yaml`. No external portal adapter may be activated
or queried without an APPROVED record in this registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "source_access_registry.yaml"


class PermissionStatus:
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    PENDING_FORMAL_REVIEW = "PENDING_FORMAL_REVIEW"
    PROHIBITED_WITHOUT_PERMISSION = "PROHIBITED_WITHOUT_PERMISSION"
    AVAILABLE_AFTER_FREE_REGISTRATION = "AVAILABLE_AFTER_FREE_REGISTRATION"
    NON_EMPIRICAL = "NON_EMPIRICAL"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class SourceAccessRecord:
    source_id: str
    display_name: str
    operator: str
    source_kind: str
    acquisition_method: str
    homepage_url: str
    search_url_pattern: str
    robots_url: str
    terms_url: str
    terms_reviewed_at: Optional[datetime]
    terms_content_sha256: str
    robots_reviewed_at: Optional[datetime]
    robots_content_sha256: str
    permission_status: str
    permission_evidence_path: str
    approved_paths: tuple[str, ...]
    maximum_requests_per_minute: int
    maximum_requests_per_day: int
    contact: str
    review_expires_at: Optional[datetime]
    notes: str

    @property
    def is_permitted_for_network_collection(self) -> bool:
        """True only if formally approved and review has not expired."""
        if self.permission_status == PermissionStatus.APPROVED:
            if self.review_expires_at and self.review_expires_at < datetime.now(timezone.utc):
                return False
            return True
        if self.permission_status == PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "display_name": self.display_name,
            "operator": self.operator,
            "source_kind": self.source_kind,
            "acquisition_method": self.acquisition_method,
            "homepage_url": self.homepage_url,
            "search_url_pattern": self.search_url_pattern,
            "robots_url": self.robots_url,
            "terms_url": self.terms_url,
            "terms_reviewed_at": (
                self.terms_reviewed_at.isoformat() if self.terms_reviewed_at else None
            ),
            "terms_content_sha256": self.terms_content_sha256,
            "robots_reviewed_at": (
                self.robots_reviewed_at.isoformat() if self.robots_reviewed_at else None
            ),
            "robots_content_sha256": self.robots_content_sha256,
            "permission_status": self.permission_status,
            "permission_evidence_path": self.permission_evidence_path,
            "approved_paths": list(self.approved_paths),
            "maximum_requests_per_minute": self.maximum_requests_per_minute,
            "maximum_requests_per_day": self.maximum_requests_per_day,
            "contact": self.contact,
            "review_expires_at": (
                self.review_expires_at.isoformat() if self.review_expires_at else None
            ),
            "is_permitted_for_network_collection": self.is_permitted_for_network_collection,
            "notes": self.notes,
        }


class SourceRegistry:
    """In-memory loaded view of source_access_registry.yaml."""

    def __init__(self, registry_file: Path = REGISTRY_PATH):
        self._registry_file = registry_file
        self._sources: dict[str, SourceAccessRecord] = {}
        self.load()

    def load(self) -> None:
        if not self._registry_file.exists():
            logger.warning(f"Source access registry not found at {self._registry_file}")
            return

        with open(self._registry_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        records: dict[str, SourceAccessRecord] = {}
        for item in data.get("sources", []):
            terms_ts = None
            if item.get("terms_reviewed_at"):
                terms_ts = datetime.fromisoformat(item["terms_reviewed_at"].replace("Z", "+00:00"))

            robots_ts = None
            if item.get("robots_reviewed_at"):
                robots_ts = datetime.fromisoformat(item["robots_reviewed_at"].replace("Z", "+00:00"))

            expiry_ts = None
            if item.get("review_expires_at"):
                expiry_ts = datetime.fromisoformat(item["review_expires_at"].replace("Z", "+00:00"))

            record = SourceAccessRecord(
                source_id=item["source_id"],
                display_name=item["display_name"],
                operator=item["operator"],
                source_kind=item["source_kind"],
                acquisition_method=item["acquisition_method"],
                homepage_url=item.get("homepage_url", ""),
                search_url_pattern=item.get("search_url_pattern", ""),
                robots_url=item.get("robots_url", ""),
                terms_url=item.get("terms_url", ""),
                terms_reviewed_at=terms_ts,
                terms_content_sha256=item.get("terms_content_sha256", ""),
                robots_reviewed_at=robots_ts,
                robots_content_sha256=item.get("robots_content_sha256", ""),
                permission_status=item.get("permission_status", PermissionStatus.PENDING),
                permission_evidence_path=item.get("permission_evidence_path", ""),
                approved_paths=tuple(item.get("approved_paths", [])),
                maximum_requests_per_minute=item.get("maximum_requests_per_minute", 0),
                maximum_requests_per_day=item.get("maximum_requests_per_day", 0),
                contact=item.get("contact", ""),
                review_expires_at=expiry_ts,
                notes=item.get("notes", ""),
            )
            records[record.source_id] = record

        self._sources = records

    def get(self, source_id: str) -> Optional[SourceAccessRecord]:
        return self._sources.get(source_id)

    def list_all(self) -> list[SourceAccessRecord]:
        return list(self._sources.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_version": "1.0.0",
            "sources": [s.to_dict() for s in self._sources.values()],
        }


_GLOBAL_REGISTRY: Optional[SourceRegistry] = None


def get_source_registry() -> SourceRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = SourceRegistry()
    return _GLOBAL_REGISTRY
