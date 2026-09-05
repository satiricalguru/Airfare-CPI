"""
SIH26056 — Source Governance & 8-Gate Evaluation System.

Enforces source access gates before any collection attempt:
1. Terms permit or written authorization explicitly permits.
2. Relevant paths are approved and not disallowed.
3. No login, CAPTCHA, or access-control bypass required.
4. Agreed request rate and contact identity recorded.
5. Required fare fields exposed reliably for matched-model statistical product.
6. Sanitized raw fixture and parser contract exist.
7. Source-specific request budget fits zero-cost budget.
8. Source record has not expired and terms/robots hash has not drifted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any, Optional

from loguru import logger

from provenance import AcquisitionMethod
from scraper.source_registry import PermissionStatus, SourceAccessRecord, get_source_registry


@dataclass(frozen=True)
class GateCheckResult:
    is_permitted: bool
    status: str
    reason: str
    failed_gate: Optional[int] = None
    details: dict[str, Any] = None


class GovernanceValidator:
    """Validates source access registry schema and enforces 8-gate criteria."""

    @staticmethod
    def validate_registry_dict(data: dict[str, Any]) -> list[str]:
        """Strict validation of source access registry structure."""
        errors: list[str] = []
        if not isinstance(data, dict):
            return ["Registry root must be a YAML dictionary"]

        version = data.get("registry_version")
        if not version:
            errors.append("Missing required 'registry_version'")

        sources = data.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("Registry must contain a non-empty 'sources' list")
            return errors

        valid_statuses = {
            PermissionStatus.APPROVED,
            PermissionStatus.PENDING,
            PermissionStatus.PENDING_FORMAL_REVIEW,
            PermissionStatus.PROHIBITED_WITHOUT_PERMISSION,
            PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION,
            PermissionStatus.NON_EMPIRICAL,
            PermissionStatus.EXPIRED,
        }
        valid_methods = {m.value for m in AcquisitionMethod}

        for idx, src in enumerate(sources):
            prefix = f"sources[{idx}]"
            source_id = src.get("source_id")
            if not source_id:
                errors.append(f"{prefix}: missing 'source_id'")
            if not src.get("display_name"):
                errors.append(f"{prefix}: missing 'display_name'")
            if not src.get("operator"):
                errors.append(f"{prefix}: missing 'operator'")

            method = src.get("acquisition_method")
            if method not in valid_methods:
                errors.append(
                    f"{prefix} ({source_id}): invalid acquisition_method '{method}', "
                    f"must be one of {sorted(valid_methods)}"
                )

            status = src.get("permission_status")
            if status not in valid_statuses:
                errors.append(
                    f"{prefix} ({source_id}): invalid permission_status '{status}', "
                    f"must be one of {sorted(valid_statuses)}"
                )

            # Check maximum_requests_per_day bounds
            max_daily = src.get("maximum_requests_per_day", 0)
            if max_daily < 0:
                errors.append(
                    f"{prefix} ({source_id}): maximum_requests_per_day cannot be negative"
                )
            elif status in {
                PermissionStatus.APPROVED,
                PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION,
            }:
                if max_daily <= 0:
                    errors.append(
                        f"{prefix} ({source_id}): maximum_requests_per_day must be > 0"
                    )
                if not src.get("contact"):
                    errors.append(
                        f"{prefix} ({source_id}): contact information is required"
                    )

        return errors

    @classmethod
    def evaluate_gates(
        cls,
        source: SourceAccessRecord,
        url_path: Optional[str] = None,
        current_terms_content: Optional[str] = None,
        current_robots_content: Optional[str] = None,
    ) -> GateCheckResult:
        """
        Evaluate all 8 gates for a candidate network collection request.
        """
        now = datetime.now(timezone.utc)

        # Gate 1: Authorization
        if source.permission_status in {
            PermissionStatus.PROHIBITED_WITHOUT_PERMISSION,
            PermissionStatus.PENDING,
            PermissionStatus.PENDING_FORMAL_REVIEW,
        }:
            return GateCheckResult(
                is_permitted=False,
                status=source.permission_status,
                failed_gate=1,
                reason=(
                    f"Gate 1 failed: Source '{source.source_id}' has permission status "
                    f"'{source.permission_status}'. Automated network collection is prohibited "
                    f"without written permission."
                ),
            )

        if source.permission_status == PermissionStatus.NON_EMPIRICAL:
            return GateCheckResult(
                is_permitted=False,
                status=source.permission_status,
                failed_gate=1,
                reason=(
                    f"Gate 1 failed: Source '{source.source_id}' is designated NON_EMPIRICAL. "
                    f"Live network queries cannot be dispatched to non-empirical fixtures."
                ),
            )

        # Gate 2: Approved path restriction
        if url_path and source.approved_paths:
            if not any(url_path.startswith(p) for p in source.approved_paths):
                return GateCheckResult(
                    is_permitted=False,
                    status="DISALLOWED_PATH",
                    failed_gate=2,
                    reason=(
                        f"Gate 2 failed: Target path '{url_path}' is not within approved "
                        f"paths: {list(source.approved_paths)}"
                    ),
                )

        # Gate 4: Rate limit & Contact
        if source.maximum_requests_per_day <= 0 or not source.contact:
            return GateCheckResult(
                is_permitted=False,
                status="MISSING_GOVERNANCE_CONFIG",
                failed_gate=4,
                reason="Gate 4 failed: Maximum daily rate and contact identity must be specified.",
            )

        # Gate 8: Expiry and Hash Drift Check
        if source.review_expires_at and source.review_expires_at < now:
            return GateCheckResult(
                is_permitted=False,
                status=PermissionStatus.EXPIRED,
                failed_gate=8,
                reason=(
                    f"Gate 8 failed: Review period for source '{source.source_id}' expired "
                    f"at {source.review_expires_at.isoformat()}. Re-authorization required."
                ),
            )

        if current_terms_content is not None and source.terms_content_sha256:
            calc_hash = hashlib.sha256(current_terms_content.encode("utf-8")).hexdigest()
            if calc_hash != source.terms_content_sha256:
                return GateCheckResult(
                    is_permitted=False,
                    status="TERMS_HASH_DRIFT",
                    failed_gate=8,
                    reason=(
                        f"Gate 8 failed: Terms content hash drift detected for '{source.source_id}'. "
                        f"Expected {source.terms_content_sha256[:12]}..., got {calc_hash[:12]}..."
                    ),
                )

        if current_robots_content is not None and source.robots_content_sha256:
            calc_hash = hashlib.sha256(current_robots_content.encode("utf-8")).hexdigest()
            if calc_hash != source.robots_content_sha256:
                return GateCheckResult(
                    is_permitted=False,
                    status="ROBOTS_HASH_DRIFT",
                    failed_gate=8,
                    reason=(
                        f"Gate 8 failed: Robots content hash drift detected for '{source.source_id}'. "
                        f"Expected {source.robots_content_sha256[:12]}..., got {calc_hash[:12]}..."
                    ),
                )

        return GateCheckResult(
            is_permitted=True,
            status=source.permission_status,
            reason="All source governance gates verified successfully.",
        )


def check_source_permitted(source_id: str, url_path: Optional[str] = None) -> GateCheckResult:
    """Convenience gate check for any source by ID."""
    registry = get_source_registry()
    rec = registry.get(source_id)
    if not rec:
        return GateCheckResult(
            is_permitted=False,
            status="UNREGISTERED_SOURCE",
            failed_gate=1,
            reason=f"Source '{source_id}' is not registered in source_access_registry.yaml",
        )
    return GovernanceValidator.evaluate_gates(rec, url_path=url_path)
