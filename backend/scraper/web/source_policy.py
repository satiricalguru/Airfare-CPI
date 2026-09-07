"""
SIH26056 — Source Access Policy Gatekeeper.

Enforces source registry gates and robots.txt restrictions before any HTTP
or browser request is issued.
"""

from __future__ import annotations

from typing import Optional
import urllib.parse
import urllib.robotparser

from loguru import logger

from scraper.governance import GovernanceValidator
from scraper.source_registry import SourceAccessRecord, get_source_registry
from scraper.web.errors import PolicyBlockError, RobotsBlockError


class SourcePolicyEnforcer:
    """Verifies source authorization and path compliance before network calls."""

    @classmethod
    def check_can_fetch(
        cls,
        source_id: str,
        target_url: str,
        user_agent: str = "AirfareCPI-Research/2.0",
        respect_robots_txt: bool = True,
        robots_txt_content: Optional[str] = None,
        allow_research_scraping: Optional[bool] = None,
    ) -> SourceAccessRecord:
        """
        Validate all gates for target_url. Returns SourceAccessRecord if allowed.
        Raises PolicyBlockError or RobotsBlockError on any gate violation.
        """
        registry = get_source_registry()
        record = registry.get(source_id)
        if not record:
            raise PolicyBlockError(
                f"Source '{source_id}' is not registered in source_access_registry.yaml"
            )

        # Parse target path
        parsed = urllib.parse.urlparse(target_url)
        path = parsed.path

        # 1. 8-Gate check
        gate_res = GovernanceValidator.evaluate_gates(
            record,
            url_path=path,
            allow_research_scraping=allow_research_scraping,
        )
        if not gate_res.is_permitted:
            raise PolicyBlockError(f"Policy gate check failed: {gate_res.reason}")

        # 2. robots.txt check if content provided and enabled
        if respect_robots_txt and robots_txt_content:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(robots_txt_content.splitlines())
            if not rp.can_fetch(user_agent, target_url):
                raise RobotsBlockError(
                    f"robots.txt disallows user-agent '{user_agent}' for '{target_url}'"
                )

        return record
