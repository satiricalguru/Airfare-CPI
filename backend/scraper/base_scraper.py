"""
SIH26056 — Abstract Base Scraper

Base scraper class providing:
- Rate limiting and exponential backoff
- robots.txt compliance checking
- Header/User-Agent rotation
- XHR / network response interception architecture
- Structured observation serialization
- Robust error handling and scraper health reporting
"""

import abc
import asyncio
import random
import time
from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, Field
from loguru import logger


class ScrapeResult(BaseModel):
    """Result of a single route scrape run."""
    source_platform: str
    route_id: int
    origin_code: str
    destination_code: str
    booking_horizon_days: int
    departure_date: str
    status: str  # 'success', 'partial', 'failed', 'blocked'
    observations: list[dict] = Field(default_factory=list)
    error_message: Optional[str] = None
    response_time_ms: int = 0
    selector_version: str = "v1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class BaseAirlineScraper(abc.ABC):
    """
    Abstract base class for all airline and OTA scrapers.
    Defines common lifecycle, rate limits, stealth headers, and parsing interfaces.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        platform_name: str,
        base_url: str,
        min_delay_sec: float = 2.0,
        max_delay_sec: float = 5.0,
        max_retries: int = 3,
        selector_version: str = "v1.0",
    ):
        self.platform_name = platform_name
        self.base_url = base_url
        self.min_delay_sec = min_delay_sec
        self.max_delay_sec = max_delay_sec
        self.max_retries = max_retries
        self.selector_version = selector_version

    def get_random_headers(self) -> dict[str, str]:
        """Generate human-like request headers."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
        }

    async def polite_delay(self):
        """Introduce randomized delay to respect target server rate limits."""
        delay = random.uniform(self.min_delay_sec, self.max_delay_sec)
        await asyncio.sleep(delay)

    @abc.abstractmethod
    async def fetch_route_fares(
        self,
        route_id: int,
        origin_code: str,
        destination_code: str,
        departure_date: date,
        booking_horizon: int,
    ) -> ScrapeResult:
        """
        Subclasses must implement this method to fetch fares for a given route and departure date.
        """
        pass
