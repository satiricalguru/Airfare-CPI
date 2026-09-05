"""
SIH26056 — Free Quota & Budget Enforcement Controller.

Enforces zero-cost API and portal request budgets:
- 80% warning threshold (logs warning and signals telemetry)
- 95% reduced-basket threshold (drops collection to 6 tracer routes)
- 100% hard stop (stops collection immediately, sets QUOTA_EXHAUSTED)
- Paid overage protection: ALLOW_PAID_OVERAGE defaults to False.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import RequestBudget, RequestUsage
from scraper.source_registry import get_source_registry


class BudgetStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    REDUCED_BASKET = "REDUCED_BASKET"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"


# 6 Tracer routes designated in Section 8 of IMPLEMENTATION_PLAN.md
TRACER_BASKET_ROUTE_CODES: tuple[str, ...] = (
    "DEL-BOM",
    "DEL-BLR",
    "BOM-BLR",
    "DEL-CCU",
    "BLR-HYD",
    "MAA-DEL",
)


@dataclass(frozen=True)
class BudgetEvaluation:
    status: BudgetStatus
    source_id: str
    can_proceed: bool
    is_reduced_basket: bool
    reason: str
    daily_limit: int
    daily_used: int
    daily_pct: float
    monthly_limit: int
    monthly_used: int
    monthly_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "source_id": self.source_id,
            "can_proceed": self.can_proceed,
            "is_reduced_basket": self.is_reduced_basket,
            "reason": self.reason,
            "daily": {
                "limit": self.daily_limit,
                "used": self.daily_used,
                "pct": round(self.daily_pct, 2),
                "remaining": max(0, self.daily_limit - self.daily_used),
            },
            "monthly": {
                "limit": self.monthly_limit,
                "used": self.monthly_used,
                "pct": round(self.monthly_pct, 2),
                "remaining": max(0, self.monthly_limit - self.monthly_used),
            },
        }


class BudgetExhaustedError(RuntimeError):
    """Raised when a collection attempt would exceed 100% of permitted quota."""
    pass


class BudgetController:
    """Manages source request budgets and enforces quota thresholds."""

    @classmethod
    async def get_or_create_budgets(
        cls, session: AsyncSession, source_id: str
    ) -> tuple[RequestBudget, RequestBudget]:
        """Ensure daily and monthly budget records exist for source_id."""
        now = datetime.now(timezone.utc)
        registry = get_source_registry()
        record = registry.get(source_id)

        # Default limits from registry or conservative standard
        daily_max = record.maximum_requests_per_day if record else 100
        # If daily is 100, default monthly is ~2000 (standard Amadeus free test tier)
        monthly_max = max(daily_max * 20, 2000)

        # 1. Daily budget
        stmt_daily = select(RequestBudget).where(
            RequestBudget.source_id == source_id,
            RequestBudget.period_type == "daily",
        )
        res_daily = await session.execute(stmt_daily)
        daily_budget = res_daily.scalar_one_or_none()
        if not daily_budget:
            daily_budget = RequestBudget(
                source_id=source_id,
                period_type="daily",
                limit_count=daily_max,
                warning_threshold_pct=80.0,
                reduced_basket_threshold_pct=95.0,
                is_hard_stop=True,
                created_at=now,
                updated_at=now,
            )
            session.add(daily_budget)

        # 2. Monthly budget
        stmt_monthly = select(RequestBudget).where(
            RequestBudget.source_id == source_id,
            RequestBudget.period_type == "monthly",
        )
        res_monthly = await session.execute(stmt_monthly)
        monthly_budget = res_monthly.scalar_one_or_none()
        if not monthly_budget:
            monthly_budget = RequestBudget(
                source_id=source_id,
                period_type="monthly",
                limit_count=monthly_max,
                warning_threshold_pct=80.0,
                reduced_basket_threshold_pct=95.0,
                is_hard_stop=True,
                created_at=now,
                updated_at=now,
            )
            session.add(monthly_budget)

        await session.flush()
        return daily_budget, monthly_budget

    @classmethod
    async def get_usages(
        cls, session: AsyncSession, source_id: str, for_date: Optional[date] = None
    ) -> tuple[RequestUsage, RequestUsage]:
        """Get or initialize today's and this month's usage records."""
        d = for_date or date.today()
        day_key = d.isoformat()
        month_key = d.strftime("%Y-%m")

        # Daily usage
        stmt_day = select(RequestUsage).where(
            RequestUsage.source_id == source_id,
            RequestUsage.period_type == "daily",
            RequestUsage.period_key == day_key,
        )
        res_day = await session.execute(stmt_day)
        day_usage = res_day.scalar_one_or_none()
        if not day_usage:
            day_usage = RequestUsage(
                source_id=source_id,
                period_type="daily",
                period_key=day_key,
                request_count=0,
                successful_requests=0,
                failed_requests=0,
            )
            session.add(day_usage)

        # Monthly usage
        stmt_month = select(RequestUsage).where(
            RequestUsage.source_id == source_id,
            RequestUsage.period_type == "monthly",
            RequestUsage.period_key == month_key,
        )
        res_month = await session.execute(stmt_month)
        month_usage = res_month.scalar_one_or_none()
        if not month_usage:
            month_usage = RequestUsage(
                source_id=source_id,
                period_type="monthly",
                period_key=month_key,
                request_count=0,
                successful_requests=0,
                failed_requests=0,
            )
            session.add(month_usage)

        await session.flush()
        return day_usage, month_usage

    @classmethod
    async def evaluate_budget(
        cls,
        session: AsyncSession,
        source_id: str,
        projected_count: int = 1,
        for_date: Optional[date] = None,
    ) -> BudgetEvaluation:
        """
        Evaluate if a collection batch of `projected_count` requests can proceed.
        Returns BudgetEvaluation with status, reduced_basket flag, and limits.
        """
        cfg = get_settings()
        allow_paid = getattr(cfg.amadeus, "allow_paid_overage", False)

        daily_budget, monthly_budget = await cls.get_or_create_budgets(session, source_id)
        day_usage, month_usage = await cls.get_usages(session, source_id, for_date)

        daily_used = day_usage.request_count
        daily_limit = daily_budget.limit_count
        daily_projected_pct = ((daily_used + projected_count) / daily_limit) * 100.0 if daily_limit > 0 else 0.0

        monthly_used = month_usage.request_count
        monthly_limit = monthly_budget.limit_count
        monthly_projected_pct = ((monthly_used + projected_count) / monthly_limit) * 100.0 if monthly_limit > 0 else 0.0

        max_pct = max(daily_projected_pct, monthly_projected_pct)

        # Check 100% Hard Stop
        if max_pct >= 100.0:
            if not allow_paid:
                reason = (
                    f"Budget hard stop: projected requests ({projected_count}) would exceed quota. "
                    f"Daily: {daily_used}/{daily_limit} ({daily_projected_pct:.1f}%), "
                    f"Monthly: {monthly_used}/{monthly_limit} ({monthly_projected_pct:.1f}%). "
                    f"ALLOW_PAID_OVERAGE is False."
                )
                logger.error(f"[{source_id}] {reason}")
                return BudgetEvaluation(
                    status=BudgetStatus.QUOTA_EXHAUSTED,
                    source_id=source_id,
                    can_proceed=False,
                    is_reduced_basket=False,
                    reason=reason,
                    daily_limit=daily_limit,
                    daily_used=daily_used,
                    daily_pct=daily_projected_pct,
                    monthly_limit=monthly_limit,
                    monthly_used=monthly_used,
                    monthly_pct=monthly_projected_pct,
                )
            else:
                logger.warning(
                    f"[{source_id}] Paid overage permitted: continuing collection beyond free quota."
                )

        # Check 95% Reduced Basket Mode
        if max_pct >= 95.0:
            reason = (
                f"Budget threshold at {max_pct:.1f}% >= 95%: operating in reduced-basket mode. "
                f"Only 6 core tracer routes will be collected to conserve quota."
            )
            logger.warning(f"[{source_id}] {reason}")
            return BudgetEvaluation(
                status=BudgetStatus.REDUCED_BASKET,
                source_id=source_id,
                can_proceed=True,
                is_reduced_basket=True,
                reason=reason,
                daily_limit=daily_limit,
                daily_used=daily_used,
                daily_pct=daily_projected_pct,
                monthly_limit=monthly_limit,
                monthly_used=monthly_used,
                monthly_pct=monthly_projected_pct,
            )

        # Check 80% Warning Threshold
        if max_pct >= 80.0:
            reason = (
                f"Budget warning: source request volume has reached {max_pct:.1f}% of quota. "
                f"Daily: {daily_used}/{daily_limit}, Monthly: {monthly_used}/{monthly_limit}."
            )
            logger.warning(f"[{source_id}] {reason}")
            return BudgetEvaluation(
                status=BudgetStatus.WARNING,
                source_id=source_id,
                can_proceed=True,
                is_reduced_basket=False,
                reason=reason,
                daily_limit=daily_limit,
                daily_used=daily_used,
                daily_pct=daily_projected_pct,
                monthly_limit=monthly_limit,
                monthly_used=monthly_used,
                monthly_pct=monthly_projected_pct,
            )

        return BudgetEvaluation(
            status=BudgetStatus.NORMAL,
            source_id=source_id,
            can_proceed=True,
            is_reduced_basket=False,
            reason="Within normal free quota bounds.",
            daily_limit=daily_limit,
            daily_used=daily_used,
            daily_pct=daily_projected_pct,
            monthly_limit=monthly_limit,
            monthly_used=monthly_used,
            monthly_pct=monthly_projected_pct,
        )

    @classmethod
    async def record_usage(
        cls,
        session: AsyncSession,
        source_id: str,
        count: int = 1,
        success: bool = True,
        for_date: Optional[date] = None,
    ) -> None:
        """Record dispatched requests towards daily and monthly quota."""
        now = datetime.now(timezone.utc)
        day_usage, month_usage = await cls.get_usages(session, source_id, for_date)

        day_usage.request_count += count
        month_usage.request_count += count

        if success:
            day_usage.successful_requests += count
            month_usage.successful_requests += count
        else:
            day_usage.failed_requests += count
            month_usage.failed_requests += count

        day_usage.last_request_at = now
        month_usage.last_request_at = now

        await session.flush()
