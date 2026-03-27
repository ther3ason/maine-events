"""
Scraper for PortlandOldPort.com/events.

Targets the public events listing page and extracts upcoming events
for the Old Port district of Portland, Maine.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from src.extractors.base_scraper import BaseScraper
from src.models import Event

logger = logging.getLogger(__name__)

VENUE_NAME = "Portland Old Port"
BASE_URL = "https://portlandoldport.com/events"


class PortlandOldPortScraper(BaseScraper):
    """
    Scraper for the Portland Old Port events listing page.

    The Old Port BID site renders events as article cards. Each card
    typically contains: event title, date string, optional description,
    and a detail/ticket link.
    """

    def __init__(self):
        super().__init__(base_url=BASE_URL)

    def parse(self, html: str) -> List[Event]:
        """
        Parses the Old Port events page HTML into Event objects.

        Args:
            html: Raw HTML string from portlandoldport.com/events.

        Returns:
            A list of validated Event instances.
        """
        soup = BeautifulSoup(html, "html.parser")
        events: List[Event] = []

        # The Old Port site uses article/card elements for each event.
        # Selectors are intentionally broad to survive minor template changes.
        event_cards = (
            soup.select("article.event")
            or soup.select(".event-card")
            or soup.select(".tribe-events-calendar-list__event")
            or soup.select("article")
        )

        if not event_cards:
            logger.warning(
                "No event cards found on %s — the page structure may have changed.",
                self.base_url,
            )
            return events

        for card in event_cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        return events

    def _parse_card(self, card: Tag) -> Optional[Event]:
        """Extracts a single Event from an HTML card element."""
        try:
            event_name = self._extract_title(card)
            if not event_name:
                logger.debug("Skipping card with no title: %s", card.get("class"))
                return None

            date_iso = self._extract_date(card)
            ticket_link = self._extract_link(card)
            description = self._extract_description(card)

            return Event(
                event_name=event_name,
                venue_name=VENUE_NAME,
                date_iso=date_iso,
                ticket_link=ticket_link,
                source_url=self.base_url,
                scraped_at_timestamp=datetime.now(timezone.utc),
                description=description,
            )
        except Exception as exc:
            logger.warning("Failed to parse event card: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private extraction helpers
    # ------------------------------------------------------------------

    def _extract_title(self, card: Tag) -> Optional[str]:
        """Returns the event title from the card, trying common selectors."""
        for selector in [
            "h2.event-title",
            "h3.event-title",
            ".tribe-event-url",
            "h2 a",
            "h3 a",
            "h2",
            "h3",
        ]:
            el = card.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_date(self, card: Tag) -> str:
        """
        Returns a date string, preferring machine-readable datetime attributes.
        Falls back to text content, then an empty string.
        """
        # Many WordPress/The Events Calendar themes use <abbr> or <time> with datetime attr
        for selector in ["abbr.tribe-events-abbr", "time", ".tribe-event-date-start"]:
            el = card.select_one(selector)
            if el:
                dt_attr = el.get("datetime") or el.get("title")
                if dt_attr:
                    return str(dt_attr)
                if el.get_text(strip=True):
                    return el.get_text(strip=True)

        # Regex fallback: look for date-like strings in the card text
        text = card.get_text(" ", strip=True)
        match = re.search(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(0)

        logger.debug("Could not extract date from card; defaulting to empty string.")
        return ""

    def _extract_link(self, card: Tag) -> Optional[str]:
        """Returns the first absolute href found in the card."""
        for selector in [".tribe-event-url", "a[href]"]:
            el = card.select_one(selector)
            if el and el.get("href"):
                href = str(el["href"])
                if href.startswith("http"):
                    return href
                if href.startswith("/"):
                    return f"https://portlandoldport.com{href}"
        return None

    def _extract_description(self, card: Tag) -> Optional[str]:
        """Returns a short description/excerpt if present."""
        for selector in [".tribe-events-calendar-list__event-description", ".excerpt", "p"]:
            el = card.select_one(selector)
            if el and el.get_text(strip=True):
                text = el.get_text(strip=True)
                return text[:300] + "…" if len(text) > 300 else text
        return None
