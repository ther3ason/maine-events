"""
Unit tests for the Event Pydantic model.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import Event


VALID_PAYLOAD = {
    "event_name": "The Black Keys",
    "venue_name": "State Theatre",
    "date_iso": "2025-08-15T20:00:00",
    "ticket_link": "https://statetheatreportland.com/events/black-keys",
    "source_url": "https://statetheatreportland.com/events",
    "scraped_at_timestamp": datetime(2025, 3, 27, 12, 0, 0, tzinfo=timezone.utc),
}


class TestEventModel:
    def test_valid_event_creates_successfully(self):
        event = Event(**VALID_PAYLOAD)
        assert event.event_name == "The Black Keys"
        assert event.venue_name == "State Theatre"

    def test_whitespace_is_stripped_from_name_fields(self):
        payload = {**VALID_PAYLOAD, "event_name": "  Reggae Night  ", "venue_name": " The Port  "}
        event = Event(**payload)
        assert event.event_name == "Reggae Night"
        assert event.venue_name == "The Port"

    def test_ticket_link_is_optional(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "ticket_link"}
        event = Event(**payload)
        assert event.ticket_link is None

    def test_description_is_optional(self):
        event = Event(**VALID_PAYLOAD)
        assert event.description is None

    def test_invalid_source_url_raises_validation_error(self):
        payload = {**VALID_PAYLOAD, "source_url": "not-a-url"}
        with pytest.raises(ValidationError):
            Event(**payload)

    def test_missing_required_field_raises_validation_error(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "event_name"}
        with pytest.raises(ValidationError):
            Event(**payload)

    def test_to_s3_dict_returns_json_serialisable_dict(self):
        event = Event(**VALID_PAYLOAD)
        result = event.to_s3_dict()
        assert isinstance(result, dict)
        assert result["event_name"] == "The Black Keys"
        # datetime should be serialised to a string
        assert isinstance(result["scraped_at_timestamp"], str)

    def test_scraped_at_timestamp_defaults_to_utc_now(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "scraped_at_timestamp"}
        payload["scraped_at_timestamp"] = None
        event = Event(**payload)
        assert isinstance(event.scraped_at_timestamp, datetime)
