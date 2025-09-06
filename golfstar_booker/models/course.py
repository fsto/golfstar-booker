"""Data models for Golfstar courses."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class Club(BaseModel):
    """Golf club information."""

    id: int
    uuid: str
    name: str
    slug: str
    terms_url: Optional[str] = None


class Location(BaseModel):
    """Geographic location coordinates."""

    lat: float
    lon: float


class Image(BaseModel):
    """Course image information."""

    id: int
    url: str


class AutoCancellationSettings(BaseModel):
    """Settings for automatic booking cancellation."""

    non_confirmed_booking_settings: dict
    unpaid_booking_settings: dict


class BookingSettings(BaseModel):
    """Booking configuration settings."""

    auto_cancellation_settings: AutoCancellationSettings


class Course(BaseModel):
    """Golf course information model."""

    id: int
    git_id: Optional[str] = None
    cdh_id: Optional[str] = None
    uuid: str
    club: Club
    name: str
    description: Optional[str] = None
    lonlat: Location
    vat: Optional[float] = None
    vat_balls: Optional[float] = None
    custom_email_information: Optional[str] = None
    important_booking_information: Optional[str] = None
    booking_information: Optional[str] = None
    booking_cancellation_limit_hours: Optional[int] = None
    pay_on_site_title: Optional[str] = None
    pay_on_site_description: Optional[str] = None
    is_active: bool
    state: str
    is_use_dynamic_pricing: bool
    booking_type: int
    tee_time_source: str
    timezone: str
    is_can_pay: bool
    is_pay_on_site_enabled: bool
    is_arrival_registration: bool
    is_arrival_registration_after_schedule: bool
    display_tee_time_days: int
    is_stub_players_enabled: bool
    belongs_to_range_context: bool
    images: List[Image] = Field(default_factory=list)
    search_field: Optional[str] = None
    type: str
    booking_settings: Optional[BookingSettings] = None
    membership_sign_up_settings: Optional[dict] = None
    golf_genius_integration: Optional[dict] = None
    discount_started_tee_times: Optional[dict] = None
    book_ongoing_tee_time: Optional[bool] = True
    script_fields: List[dict] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Get a formatted display name for the course."""
        return f"{self.name} ({self.club.name})"

    @property
    def coordinates(self) -> tuple[float, float]:
        """Get course coordinates as a tuple."""
        return (self.lonlat.lat, self.lonlat.lon)
