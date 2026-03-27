"""
Unit tests for the Ticketmaster scraper.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extractors.ticketmaster import TicketmasterScraper

SAMPLE_RAW_EVENT = {
    "name": "Carly Rae Jepsen",
    "url": "https://www.ticketmaster.com/carly-rae-jepsen-portland/event/123",
    "dates": {"start": {"dateTime": "2026-08-10T20:00:00Z", "localDate": "2026-08-10"}},
    "_embedded": {"venues": [{"name": "Cross Insurance Arena"}]},
    "priceRanges": [{"min": 45.0, "max": 95.0, "currency": "USD"}],
}


@pytest.fixture
def scraper():
    with patch.dict("os.environ", {"TICKETMASTER_API_KEY": "test-key"}):
        s = TicketmasterScraper()
        s.session = MagicMock()
        return s


def _mock_response(events, total_pages=1, page=0):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "_embedded": {"events": events},
        "page": {"totalPages": total_pages, "number": page},
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestTicketmasterScraper:
    def test_raises_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EnvironmentError, match="TICKETMASTER_API_KEY"):
                TicketmasterScraper()

    def test_run_returns_events(self, scraper):
        scraper.session.get.return_value = _mock_response([SAMPLE_RAW_EVENT])
        events = scraper.run()
        assert len(events) == 1
        assert events[0].event_name == "Carly Rae Jepsen"
        assert events[0].venue_name == "Cross Insurance Arena"

    def test_run_stops_on_empty_embedded(self, scraper):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"_embedded": {}, "page": {"totalPages": 1}}
        mock_resp.raise_for_status = MagicMock()
        scraper.session.get.return_value = mock_resp
        events = scraper.run()
        assert events == []

    def test_run_handles_request_exception(self, scraper):
        scraper.session.get.side_effect = requests.RequestException("timeout")
        events = scraper.run()
        assert events == []

    def test_run_paginates(self, scraper):
        page1 = _mock_response([SAMPLE_RAW_EVENT], total_pages=2, page=0)
        page2 = _mock_response([{**SAMPLE_RAW_EVENT, "name": "Another Act"}], total_pages=2, page=1)
        scraper.session.get.side_effect = [page1, page2]
        events = scraper.run()
        assert len(events) == 2

    def test_parse_event_skips_empty_name(self, scraper):
        result = scraper._parse_event({**SAMPLE_RAW_EVENT, "name": ""})
        assert result is None

    def test_parse_event_prefers_datetime_over_local_date(self, scraper):
        result = scraper._parse_event(SAMPLE_RAW_EVENT)
        assert result.date_iso == "2026-08-10T20:00:00Z"

    def test_parse_event_falls_back_to_local_date(self, scraper):
        raw = {**SAMPLE_RAW_EVENT, "dates": {"start": {"localDate": "2026-08-10"}}}
        result = scraper._parse_event(raw)
        assert result.date_iso == "2026-08-10"

    def test_extract_description_price_range(self, scraper):
        result = scraper._parse_event(SAMPLE_RAW_EVENT)
        assert result.description == "$45 - $95"

    def test_extract_description_min_only(self, scraper):
        raw = {**SAMPLE_RAW_EVENT, "priceRanges": [{"min": 20.0, "currency": "USD"}]}
        result = scraper._parse_event(raw)
        assert result.description == "From $20"

    def test_extract_description_no_price(self, scraper):
        raw = {**SAMPLE_RAW_EVENT, "priceRanges": None}
        result = scraper._parse_event(raw)
        assert result.description is None

    def test_api_key_injected_into_params(self, scraper):
        scraper.session.get.return_value = _mock_response([])
        scraper.run()
        call_kwargs = scraper.session.get.call_args
        params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
        assert params.get("apikey") == "test-key"
