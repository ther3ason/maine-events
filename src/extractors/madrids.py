"""
Scraper for Live at Madrid's (liveatmadrids.com/calendar).

The calendar page is a Webflow CMS site — events are server-rendered into
.home_events-preview_item cards with date, time, title, and a Tixr ticket link.
No pagination; all upcoming events are on a single page.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import cloudscraper
from bs4 import BeautifulSoup, Tag

from src.models import Event

logger = logging.getLogger(__name__)

VENUE_NAME = "Live at Madrid's"
BASE_URL = "https://www.liveatmadrids.com/calendar"


class MadridsScraper:

    def __init__(self):
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; PortlandEventsBot/1.0; "
                "+https://github.com/TheR3ason/maine-events)"
            )
        })

    def run(self) -> List[Event]:
        try:
            response = self.session.get(BASE_URL, timeout=15)
            response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", BASE_URL, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select(".home_events-preview_item.w-dyn-item")

        if not cards:
            logger.warning("No event cards found — page structure may have changed.")
            return []

        events = []
        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        logger.info("MadridsScraper extracted %d events", len(events))
        return events

    def _parse_card(self, card: Tag) -> Optional[Event]:
        try:
            title_el = card.select_one("h3.heading-style-h5")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            if "happy hour" in title.lower():
                logger.debug("Filtered out happy hour event: %s", title)
                return None


            # Date and time sit in sequential .home_events-preview_header-text divs
            # separated by a "|" div: [date, |, time]
            date_parts = [
                el.get_text(strip=True)
                for el in card.select(".home_events-preview_header-text")
                if el.get_text(strip=True) != "|"
            ]
            date_iso = " ".join(date_parts)  # e.g. "April 3, 2026 7:30 pm"

            ticket_el = card.select_one("a.button.is-secondary")
            ticket_link = ticket_el["href"] if ticket_el and ticket_el.get("href") else None

            return Event(
                event_name=title,
                venue_name=VENUE_NAME,
                date_iso=date_iso,
                ticket_link=ticket_link,
                source_url=BASE_URL,
                scraped_at_timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.warning("Failed to parse card: %s", exc)
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = MadridsScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned — the site may have changed structure.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
