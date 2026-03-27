"""
Unit tests for the Live at Madrid's scraper.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.extractors.madrids import MadridsScraper

SAMPLE_CARD_HTML = """
<div class="home_events-preview_item w-dyn-item">
  <div class="home_events-preview_card-content">
    <div class="home_events-preview_date-wrapper">
      <div class="home_events-preview_header-text">April 3, 2026</div>
      <div class="home_events-preview_header-text dash-padding">|</div>
      <div class="home_events-preview_header-text">7:30 pm</div>
    </div>
    <h3 class="heading-style-h5">Gwynne and the Tonics</h3>
    <a class="button is-secondary w-inline-block"
       href="https://www.tixr.com/groups/liveatmadrids/events/gwynne-179448">
      Get Tickets
    </a>
  </div>
</div>
"""

HAPPY_HOUR_CARD_HTML = """
<div class="home_events-preview_item w-dyn-item">
  <div class="home_events-preview_card-content">
    <div class="home_events-preview_date-wrapper">
      <div class="home_events-preview_header-text">April 4, 2026</div>
      <div class="home_events-preview_header-text dash-padding">|</div>
      <div class="home_events-preview_header-text">4:00 pm</div>
    </div>
    <h3 class="heading-style-h5">Happy Hour in The Lounge: Some Band</h3>
    <a class="button is-secondary w-inline-block"
       href="https://www.tixr.com/groups/liveatmadrids/events/happy-hour-182879">
      Get Tickets
    </a>
  </div>
</div>
"""

FULL_PAGE_HTML = f"<html><body>{SAMPLE_CARD_HTML}{HAPPY_HOUR_CARD_HTML}</body></html>"


@pytest.fixture
def scraper():
    with patch("cloudscraper.create_scraper"):
        s = MadridsScraper()
        s.session = MagicMock()
        return s


def _mock_response(html, status=200):
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.status_code = status
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestMadridsScraper:
    def test_run_returns_events(self, scraper):
        scraper.session.get.return_value = _mock_response(FULL_PAGE_HTML)
        events = scraper.run()
        assert len(events) == 1
        assert events[0].event_name == "Gwynne and the Tonics"

    def test_run_filters_happy_hour(self, scraper):
        scraper.session.get.return_value = _mock_response(FULL_PAGE_HTML)
        events = scraper.run()
        assert all("happy hour" not in e.event_name.lower() for e in events)

    def test_run_returns_empty_on_no_cards(self, scraper):
        scraper.session.get.return_value = _mock_response("<html><body></body></html>")
        events = scraper.run()
        assert events == []

    def test_run_returns_empty_on_request_failure(self, scraper):
        scraper.session.get.side_effect = Exception("network error")
        events = scraper.run()
        assert events == []

    def test_event_fields_parsed_correctly(self, scraper):
        scraper.session.get.return_value = _mock_response(FULL_PAGE_HTML)
        event = scraper.run()[0]
        assert event.venue_name == "Live at Madrid's"
        assert event.date_iso == "April 3, 2026 7:30 pm"
        assert "tixr.com" in str(event.ticket_link)

    def test_card_without_title_returns_none(self, scraper):
        html = """
        <html><body>
        <div class="home_events-preview_item w-dyn-item">
          <div class="home_events-preview_date-wrapper">
            <div class="home_events-preview_header-text">April 5, 2026</div>
          </div>
        </div>
        </body></html>
        """
        scraper.session.get.return_value = _mock_response(html)
        events = scraper.run()
        assert events == []

    def test_card_without_ticket_link_still_creates_event(self, scraper):
        html = """
        <html><body>
        <div class="home_events-preview_item w-dyn-item">
          <div class="home_events-preview_header-text">April 6, 2026</div>
          <div class="home_events-preview_header-text">|</div>
          <div class="home_events-preview_header-text">8:00 pm</div>
          <h3 class="heading-style-h5">No Ticket Show</h3>
        </div>
        </body></html>
        """
        scraper.session.get.return_value = _mock_response(html)
        events = scraper.run()
        assert len(events) == 1
        assert events[0].ticket_link is None
