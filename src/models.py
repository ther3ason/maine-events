"""
Pydantic data models for the Portland Events ETL pipeline.

The Event model is the canonical unit of data throughout the pipeline.
Raw scraped data is coerced into this schema before being written to S3.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, AnyHttpUrl, field_validator


class Event(BaseModel):
    """
    Represents a single scraped event from a Greater Portland venue.

    Attributes:
        event_name:          Display title of the event.
        venue_name:          Human-readable name of the hosting venue.
        date_iso:            Event date/time in ISO 8601 format (UTC preferred).
        ticket_link:         URL where tickets can be purchased or reserved.
        source_url:          The page URL this event was scraped from.
        scraped_at_timestamp: UTC timestamp of when scraping occurred.
        description:         Optional short description or subtitle.
    """

    event_name: str
    venue_name: str
    date_iso: str
    ticket_link: Optional[AnyHttpUrl] = None
    source_url: AnyHttpUrl
    scraped_at_timestamp: datetime
    description: Optional[str] = None

    @field_validator("scraped_at_timestamp", mode="before")
    @classmethod
    def default_to_utc_now(cls, v):
        """If no timestamp supplied, default to current UTC time."""
        if v is None:
            return datetime.now(timezone.utc)
        return v

    @field_validator("event_name", "venue_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = {
        "json_encoders": {datetime: lambda dt: dt.isoformat()},
        "populate_by_name": True,
    }

    def to_s3_dict(self) -> dict:
        """Returns a JSON-serialisable dict suitable for S3/Athena storage."""
        return self.model_dump(mode="json")
