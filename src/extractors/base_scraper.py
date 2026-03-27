"""
Base scraper abstract class for the Portland Events ETL pipeline.

All venue-specific scrapers inherit from BaseScraper and implement
the parse() method for their respective HTML structure.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import Event

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PortlandEventsBot/1.0; "
        "+https://github.com/TheR3ason/maine-events)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)


class BaseScraper(ABC):
    """
    Abstract base class for all venue scrapers.

    Subclasses must implement parse() to transform raw HTML into
    a list of validated Event objects.
    """

    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Creates a requests Session with retry logic and standard headers."""
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(DEFAULT_HEADERS)
        return session

    def fetch_page(self, url: str) -> str:
        """
        Fetches raw HTML from the given URL.

        Args:
            url: The fully-qualified URL to fetch.

        Returns:
            The raw HTML content as a string.

        Raises:
            requests.HTTPError: On 4xx/5xx responses.
            requests.ConnectionError: On network failures.
            requests.Timeout: When the request exceeds self.timeout.
        """
        logger.info("Fetching page: %s", url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            logger.debug("Received %d bytes from %s", len(response.content), url)
            return response.text
        except requests.HTTPError as exc:
            logger.error("HTTP error fetching %s: %s", url, exc)
            raise
        except requests.ConnectionError as exc:
            logger.error("Connection error fetching %s: %s", url, exc)
            raise
        except requests.Timeout:
            logger.error("Request timed out after %ds for %s", self.timeout, url)
            raise

    @abstractmethod
    def parse(self, html: str) -> List[Event]:
        """
        Parses raw HTML and returns a list of validated Event objects.

        Args:
            html: Raw HTML string returned by fetch_page().

        Returns:
            A list of Event model instances.
        """

    def run(self) -> List[Event]:
        """
        Orchestrates fetch + parse for the scraper's base_url.

        Returns:
            A list of Event model instances, or an empty list on failure.
        """
        try:
            html = self.fetch_page(self.base_url)
            events = self.parse(html)
            logger.info(
                "%s extracted %d events from %s",
                self.__class__.__name__,
                len(events),
                self.base_url,
            )
            return events
        except Exception as exc:
            logger.error(
                "%s failed to run against %s: %s",
                self.__class__.__name__,
                self.base_url,
                exc,
            )
            return []
