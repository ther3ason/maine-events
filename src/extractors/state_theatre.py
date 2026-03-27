"""
Scraper for State Theatre Portland (statetheatreportland.com).

Listing page: /state-theatre-listing/
Events live in <ul id="myList"> — each <li> contains a .list-view-details.vevent
block with machine-readable date, headliner, support act, and Ticketmaster link.

Pagination: the site lazy-loads additional pages via AJAX at
/state-theatre-listing/?paged=N — this scraper fetches all pages.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from src.extractors.base_scraper import BaseScraper
from src.models import Event

logger = logging.getLogger(__name__)

VENUE_NAME = "State Theatre Portland"
BASE_URL = "https://statetheatreportland.com/state-theatre-listing/"


class StateTheatreScraper(BaseScraper):

    def __init__(self):
        super().__init__(base_url=BASE_URL)

    def parse(self, html: str) -> List[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: List[Event] = []

        cards = soup.select("ul#myList li")
        if not cards:
            logger.warning("No events found in <ul id='myList'> — page structure may have changed.")
            return events

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        return events

    def _parse_card(self, card: Tag) -> Optional[Event]:
        try:
            # Details and ticket price are siblings inside .list-view-item
            item = card.select_one(".list-view-item") or card
            details = item.select_one(".list-view-details.vevent") or item

            name = self._extract_title(details)
            if not name:
                return None

            return Event(
                event_name=name,
                venue_name=VENUE_NAME,
                date_iso=self._extract_date(details),
                ticket_link=self._extract_ticket_link(item),
                source_url=self._extract_event_url(details) or self.base_url,
                scraped_at_timestamp=datetime.now(timezone.utc),
                description=self._extract_description(details),
            )
        except Exception as exc:
            logger.warning("Failed to parse event card: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Extraction helpers — keyed to the actual site DOM
    # ------------------------------------------------------------------

    def _extract_title(self, details: Tag) -> Optional[str]:
        # <h1 class="headliners summary"><a href="/events/...">Event Name</a></h1>
        el = details.select_one("h1.headliners.summary") or details.select_one("h1.headliners")
        if el:
            return el.get_text(strip=True)
        return None

    def _extract_date(self, details: Tag) -> str:
        # <h2 class="dates" itemprop="startDate" content="2025-09-12">Friday September 12</h2>
        el = details.select_one("h2.dates")
        if el:
            machine_date = el.get("content")
            if machine_date:
                return str(machine_date)
            return el.get_text(strip=True)

        # Fallback: regex over card text
        text = details.get_text(" ", strip=True)
        match = re.search(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
            text,
            re.IGNORECASE,
        )
        return match.group(0) if match else ""

    def _extract_ticket_link(self, details: Tag) -> Optional[str]:
        # <h3 class="ticket-link primary-link"><a href="https://www.ticketmaster.com/...">TICKETS</a></h3>
        el = details.select_one("h3.ticket-link.primary-link a")
        if el and el.get("href", "").startswith("http"):
            return str(el["href"])
        return None

    def _extract_event_url(self, details: Tag) -> Optional[str]:
        # The headliner <a> links to the individual event page
        el = details.select_one("h1.headliners a")
        if el and el.get("href"):
            href = str(el["href"])
            return href if href.startswith("http") else f"https://statetheatreportland.com{href}"
        return None

    def _extract_description(self, details: Tag) -> Optional[str]:
        # <h2 class="supports description">with opener name</h2>
        support = details.select_one("h2.supports.description")
        presenter = details.select_one("h2.topline-info")

        parts = []
        if presenter and presenter.get_text(strip=True):
            parts.append(presenter.get_text(strip=True))
        if support and support.get_text(strip=True):
            parts.append(support.get_text(strip=True))

        return " | ".join(parts) if parts else None


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = StateTheatreScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned — the site may have changed structure.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
