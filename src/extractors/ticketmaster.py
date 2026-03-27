"""
Ticketmaster Discovery API v2 scraper.

Fetches upcoming events for a given venue by:
  1. Looking up the venue's Ticketmaster ID via /venues
  2. Querying /events filtered by that venue ID

Requires a TICKETMASTER_API_KEY environment variable.
Register for a free key at https://developer.ticketmaster.com/

Rate limits: 5,000 calls/day, 5 requests/second.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import Event

logger = logging.getLogger(__name__)

API_BASE = "https://app.ticketmaster.com/discovery/v2"
PAGE_SIZE = 50


class TicketmasterScraper:
    """
    Fetches events for a specific venue from the Ticketmaster Discovery API.

    Args:
        venue_name:  Venue name as it appears on Ticketmaster (used for lookup).
        city:        City name to narrow the venue search.
        state_code:  Two-letter US state code (default: ME).
    """

    def __init__(self, venue_name: str, city: str = "Portland", state_code: str = "ME"):
        self.venue_name = venue_name
        self.city = city
        self.state_code = state_code
        self.api_key = os.getenv("TICKETMASTER_API_KEY")

        if not self.api_key:
            raise EnvironmentError(
                "TICKETMASTER_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )

        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def _get(self, path: str, params: dict) -> dict:
        params["apikey"] = self.api_key
        response = self.session.get(f"{API_BASE}{path}", params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Venue ID lookup
    # ------------------------------------------------------------------

    def get_venue_id(self) -> Optional[str]:
        """
        Resolves the Ticketmaster venue ID for self.venue_name.

        Returns the ID of the first matching venue, or None if not found.
        """
        logger.info("Looking up Ticketmaster venue ID for '%s'", self.venue_name)
        try:
            data = self._get("/venues", {
                "keyword": self.venue_name,
                "city": self.city,
                "stateCode": self.state_code,
                "countryCode": "US",
            })
        except requests.RequestException as exc:
            logger.error("Venue lookup failed: %s", exc)
            return None

        venues = data.get("_embedded", {}).get("venues", [])
        if not venues:
            logger.warning("No Ticketmaster venue found for '%s'", self.venue_name)
            return None

        venue_id = venues[0]["id"]
        logger.info("Resolved '%s' -> venue ID %s", self.venue_name, venue_id)
        return venue_id

    # ------------------------------------------------------------------
    # Event fetching
    # ------------------------------------------------------------------

    def run(self) -> List[Event]:
        """Fetches all upcoming events for the venue."""
        venue_id = self.get_venue_id()
        if not venue_id:
            return []

        all_events: List[Event] = []
        page = 0

        while True:
            try:
                data = self._get("/events", {
                    "venueId": venue_id,
                    "size": PAGE_SIZE,
                    "page": page,
                    "sort": "date,asc",
                    "countryCode": "US",
                })
            except requests.RequestException as exc:
                logger.error("Events request failed on page %d: %s", page, exc)
                break

            embedded = data.get("_embedded", {})
            raw_events = embedded.get("events", [])
            if not raw_events:
                break

            for raw in raw_events:
                event = self._parse_event(raw)
                if event:
                    all_events.append(event)

            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)
            logger.info(
                "Page %d/%d — %d events collected",
                page + 1, total_pages, len(all_events)
            )

            if page + 1 >= total_pages:
                break
            page += 1

        logger.info(
            "%s extracted %d events for '%s'",
            self.__class__.__name__, len(all_events), self.venue_name,
        )
        return all_events

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_event(self, raw: dict) -> Optional[Event]:
        try:
            name = raw.get("name", "").strip()
            if not name:
                return None

            venue_name = (
                raw.get("_embedded", {})
                   .get("venues", [{}])[0]
                   .get("name", self.venue_name)
            )

            date_iso = (
                raw.get("dates", {})
                   .get("start", {})
                   .get("dateTime")
                or raw.get("dates", {})
                   .get("start", {})
                   .get("localDate", "")
            )

            return Event(
                event_name=name,
                venue_name=venue_name,
                date_iso=str(date_iso),
                ticket_link=raw.get("url"),
                source_url=raw.get("url") or f"{API_BASE}/events",
                scraped_at_timestamp=datetime.now(timezone.utc),
                description=self._extract_description(raw),
            )
        except Exception as exc:
            logger.warning("Failed to parse event '%s': %s", raw.get("name"), exc)
            return None

    def _extract_description(self, raw: dict) -> Optional[str]:
        """Returns price range string if available (e.g. '$35 - $75')."""
        price_ranges = raw.get("priceRanges")
        if not price_ranges:
            return None
        pr = price_ranges[0]
        low, high = pr.get("min"), pr.get("max")
        currency = pr.get("currency", "USD")
        symbol = "$" if currency == "USD" else currency
        if low and high:
            return f"{symbol}{low:.0f} - {symbol}{high:.0f}"
        if low:
            return f"From {symbol}{low:.0f}"
        return None
