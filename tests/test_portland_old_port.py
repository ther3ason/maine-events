"""
Unit tests for the Portland Old Port scraper.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.portland_old_port import PortlandOldPortScraper

SAMPLE_EVENT = {
    "title": "Jazz Night at Arcadia",
    "start_date": "2026-06-15 19:00:00",
    "url": "https://www.portlandoldport.com/pop-event/jazz-night/",
    "website": "https://arcadiaportland.com/",
    "venue": {"venue": "Arcadia"},
    "excerpt": "A great jazz night.",
}

HAPPY_HOUR_EVENT = {
    "title": "Happy Hour at Gritty's",
    "start_date": "2026-06-15 16:00:00",
    "url": "https://www.portlandoldport.com/pop-event/happy-hour/",
    "website": "https://grittys.com/",
    "venue": {"venue": "Gritty McDuff's"},
    "excerpt": "",
}


class TestPortlandOldPortScraper:
    def setup_method(self):
        with patch("cloudscraper.create_scraper"):
            self.scraper = PortlandOldPortScraper()
            self.scraper.session = MagicMock()

    def _mock_response(self, events, total_pages=1):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"events": events, "total_pages": total_pages}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_run_returns_events(self):
        self.scraper.session.get.return_value = self._mock_response([SAMPLE_EVENT])
        events = self.scraper.run()
        assert len(events) == 1
        assert events[0].event_name == "Jazz Night at Arcadia"

    def test_run_filters_happy_hour(self):
        self.scraper.session.get.return_value = self._mock_response(
            [SAMPLE_EVENT, HAPPY_HOUR_EVENT]
        )
        events = self.scraper.run()
        assert len(events) == 1
        assert all("happy hour" not in e.event_name.lower() for e in events)

    def test_run_stops_on_empty_events(self):
        self.scraper.session.get.return_value = self._mock_response([])
        events = self.scraper.run()
        assert events == []

    def test_run_handles_request_exception(self):
        self.scraper.session.get.side_effect = Exception("connection failed")
        events = self.scraper.run()
        assert events == []

    def test_run_paginates(self):
        page1 = self._mock_response([SAMPLE_EVENT], total_pages=2)
        page2 = self._mock_response([{**SAMPLE_EVENT, "title": "Second Event"}], total_pages=2)
        empty = self._mock_response([])
        self.scraper.session.get.side_effect = [page1, page2, empty]
        events = self.scraper.run()
        assert len(events) == 2

    def test_parse_event_returns_none_for_empty_title(self):
        result = self.scraper._parse_event({"title": "", "url": "https://example.com"})
        assert result is None

    def test_parse_event_falls_back_to_default_venue(self):
        raw = {**SAMPLE_EVENT, "venue": {}}
        result = self.scraper._parse_event(raw)
        assert result.venue_name == "Portland Old Port"

    def test_parse_event_uses_html_entities_in_venue(self):
        raw = {**SAMPLE_EVENT, "venue": {"venue": "Bird &amp; Co."}}
        result = self.scraper._parse_event(raw)
        assert result.venue_name == "Bird & Co."

    def test_extract_description_truncates_long_excerpt(self):
        raw = {**SAMPLE_EVENT, "excerpt": "x" * 400}
        result = self.scraper._parse_event(raw)
        assert result.description.endswith("…")
        assert len(result.description) <= 304

    def test_extract_description_returns_none_when_empty(self):
        raw = {**SAMPLE_EVENT, "excerpt": ""}
        result = self.scraper._parse_event(raw)
        assert result.description is None
