"""
Scraper for Portland Old Port events (portlandoldport.com).

Uses The Events Calendar REST API (/wp-json/tribe/events/v1/events) rather
than HTML scraping — the listing page renders via JavaScript AJAX and the
site is behind Cloudflare, making the API a more reliable extraction path.

Events titled "Happy Hour ..." are filtered out as low-signal noise.
"""

import logging
from datetime import date, datetime, timezone
from html import unescape
from typing import List, Optional

import cloudscraper

from src.models import Event

logger = logging.getLogger(__name__)

VENUE_NAME = "Portland Old Port"
API_BASE = "https://www.portlandoldport.com/wp-json/tribe/events/v1/events"
PER_PAGE = 50
HAPPY_HOUR_FILTER = "happy hour"

# Entertainment-relevant category IDs from The Events Calendar taxonomy.
# Excludes high-volume noise categories (Happy Hour, Food & Drink specials, etc.)
# IDs: Concert, Live Music, Live Entertainment, Music, Music Event, Live Show,
#      Festival, Performance, Comedy Night, Drag Show, Theatre
ENTERTAINMENT_CATEGORIES = "3962,3966,3828,3964,3967,4196,3883,3958,4392,4408,4218"


class PortlandOldPortScraper:
    """
    Scraper for Portland Old Port events using The Events Calendar REST API.

    Fetches all upcoming events, one page at a time, and converts each
    API response into a validated Event object.
    """

    def __init__(self):
        # cloudscraper handles Cloudflare's JS challenge transparently
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; PortlandEventsBot/1.0; "
                "+https://github.com/TheR3ason/maine-events)"
            )
        })

    def run(self) -> List[Event]:
        """Fetches all upcoming events from the API across all pages."""
        all_events: List[Event] = []
        page = 1
        today = date.today().isoformat()

        while True:
            params = {
                "per_page": PER_PAGE,
                "page": page,
                "status": "publish",
                "start_date": today,
                "categories": ENTERTAINMENT_CATEGORIES,
            }

            try:
                response = self.session.get(API_BASE, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.error("API request failed on page %d: %s", page, exc)
                break

            raw_events = data.get("events", [])
            if not raw_events:
                break

            for raw in raw_events:
                event = self._parse_event(raw)
                if event:
                    all_events.append(event)

            total_pages = data.get("total_pages", 1)
            logger.info("Page %d/%d — %d events collected so far", page, total_pages, len(all_events))

            if page >= total_pages:
                break
            page += 1

        logger.info("PortlandOldPortScraper extracted %d events", len(all_events))
        return all_events

    def _parse_event(self, raw: dict) -> Optional[Event]:
        """Converts a single API event dict into an Event model, or None if filtered."""
        try:
            title = unescape(raw.get("title", "")).strip()
            if not title:
                return None

            if HAPPY_HOUR_FILTER in title.lower():
                logger.debug("Filtered out happy hour event: %s", title)
                return None

            venue_name = unescape(
                raw.get("venue", {}).get("venue", VENUE_NAME)
            ).strip() or VENUE_NAME

            return Event(
                event_name=title,
                venue_name=venue_name,
                date_iso=raw.get("start_date", ""),
                ticket_link=raw.get("website") or None,
                source_url=raw.get("url") or API_BASE,
                scraped_at_timestamp=datetime.now(timezone.utc),
                description=self._extract_description(raw),
            )
        except Exception as exc:
            logger.warning("Failed to parse event %r: %s", raw.get("title"), exc)
            return None

    def _extract_description(self, raw: dict) -> Optional[str]:
        excerpt = raw.get("excerpt", "").strip()
        if excerpt:
            return excerpt[:300] + "…" if len(excerpt) > 300 else excerpt
        return None


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = PortlandOldPortScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned — the API may be unavailable.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
