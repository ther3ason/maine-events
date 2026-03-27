"""
Ticketmaster Discovery API v2 scraper.

Fetches all upcoming ticketed events in Portland, ME across all venues.
Venue name is pulled directly from the API response on each event.

Requires TICKETMASTER_API_KEY environment variable.
Register for a free key at https://developer.ticketmaster.com/

Rate limits: 5,000 calls/day, 5 requests/second.
"""

import json
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
    """Fetches all upcoming events in Portland, ME from the Ticketmaster Discovery API."""

    def __init__(self):
        self.api_key = os.getenv("TICKETMASTER_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "TICKETMASTER_API_KEY is not set. "
                "Copy .env.example to .env and add your Consumer Key."
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

    def run(self) -> List[Event]:
        """Fetches all upcoming Portland, ME events across all venues."""
        all_events: List[Event] = []
        page = 0

        while True:
            try:
                data = self._get("/events", {
                    "city": "Portland",
                    "stateCode": "ME",
                    "countryCode": "US",
                    "size": PAGE_SIZE,
                    "page": page,
                    "sort": "date,asc",
                })
            except requests.RequestException as exc:
                logger.error("Events request failed on page %d: %s", page, exc)
                break

            raw_events = data.get("_embedded", {}).get("events", [])
            if not raw_events:
                break

            for raw in raw_events:
                event = self._parse_event(raw)
                if event:
                    all_events.append(event)

            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)
            logger.info("Page %d/%d — %d events collected", page + 1, total_pages, len(all_events))

            if page + 1 >= total_pages:
                break
            page += 1

        logger.info("TicketmasterScraper extracted %d events", len(all_events))
        return all_events

    def _parse_event(self, raw: dict) -> Optional[Event]:
        try:
            name = raw.get("name", "").strip()
            if not name:
                return None

            venue_name = (
                raw.get("_embedded", {})
                   .get("venues", [{}])[0]
                   .get("name", "Unknown Venue")
            )

            date_iso = (
                raw.get("dates", {}).get("start", {}).get("dateTime")
                or raw.get("dates", {}).get("start", {}).get("localDate", "")
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
        symbol = "$"
        if low and high:
            return f"{symbol}{low:.0f} - {symbol}{high:.0f}"
        if low:
            return f"From {symbol}{low:.0f}"
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = TicketmasterScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
