"""
Unit tests for the BaseScraper abstract class.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extractors.base_scraper import BaseScraper
from src.models import Event


class ConcreteScraper(BaseScraper):
    """Minimal concrete implementation for testing the abstract base."""

    def parse(self, html: str):
        return []


class TestBaseScraper:
    def setup_method(self):
        self.scraper = ConcreteScraper(base_url="https://example.com")

    def test_session_has_user_agent_header(self):
        assert "PortlandEventsBot" in self.scraper.session.headers["User-Agent"]

    @patch("requests.Session.get")
    def test_fetch_page_returns_text_on_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html>Hello</html>"
        mock_response.content = b"<html>Hello</html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.scraper.fetch_page("https://example.com")
        assert result == "<html>Hello</html>"

    @patch("requests.Session.get")
    def test_fetch_page_raises_on_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            self.scraper.fetch_page("https://example.com/missing")

    @patch("requests.Session.get")
    def test_run_returns_empty_list_on_network_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("unreachable")
        result = self.scraper.run()
        assert result == []
