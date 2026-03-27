"""
Scraper for Thompson's Point (statetheatreportland.com/thompsons-point-listing/).

Thompson's Point is an outdoor waterfront amphitheater in Portland, ME,
operated by State Theatre. The listing page shares the same DOM structure
as the State Theatre listing, so this scraper reuses StateTheatreScraper
with updated constants.
"""

import logging

from src.extractors.state_theatre import StateTheatreScraper

logger = logging.getLogger(__name__)

VENUE_NAME = "Thompson's Point"
BASE_URL = "https://statetheatreportland.com/thompsons-point-listing/"


class ThompsonsPointScraper(StateTheatreScraper):

    def __init__(self):
        # Skip StateTheatreScraper.__init__ and call BaseScraper directly
        super(StateTheatreScraper, self).__init__(base_url=BASE_URL)
        self.venue_name = VENUE_NAME

    def _parse_card(self, card):
        event = super()._parse_card(card)
        if event:
            event.venue_name = VENUE_NAME
        return event


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    scraper = ThompsonsPointScraper()
    events = scraper.run()

    if not events:
        print("\nNo events returned — the site may have changed structure.")
    else:
        print(f"\nFound {len(events)} event(s). Showing first 3:\n")
        for event in events[:3]:
            print(json.dumps(event.to_s3_dict(), indent=2))
            print("-" * 60)
