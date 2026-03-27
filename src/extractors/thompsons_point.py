"""
Thompson's Point — Ticketmaster Discovery API scraper.

Thin wrapper around TicketmasterScraper configured for Thompson's Point Portland.
Requires TICKETMASTER_API_KEY environment variable.
"""

import json
import logging

from src.extractors.ticketmaster import TicketmasterScraper

logger = logging.getLogger(__name__)


class ThompsonsPointScraper(TicketmasterScraper):
    def __init__(self):
        super().__init__(venue_name="Thompson's Point", city="Portland", state_code="ME")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = ThompsonsPointScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
