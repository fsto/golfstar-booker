"""Data models for tee times and availability."""

from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field
from decimal import Decimal


class Money(BaseModel):
    """Money/price information."""

    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    formatted: Optional[str] = None


class TeeTimeCourse(BaseModel):
    """Simplified course info for tee time responses."""

    id: int
    uuid: str
    name: str
    club_name: Optional[str] = None


class TeeTimeCategory(BaseModel):
    """Tee time category information."""

    id: Optional[int] = None
    name: Optional[str] = None
    uuid: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_use_same_name: Optional[bool] = None
    custom_name: Optional[str] = None
    custom_description: Optional[str] = None
    display: Optional[str] = None
    tee_time_bookable: Optional[bool] = None


class Space(BaseModel):
    """Space/slot information."""

    id: Optional[int] = None
    uuid: Optional[str] = None
    name: Optional[str] = None


class TeeTime(BaseModel):
    """Tee time availability slot."""

    id: Optional[int] = None
    uuid: str
    from_time: Optional[datetime] = Field(alias="from", default=None)
    to_time: Optional[datetime] = Field(alias="to", default=None)
    interval: Optional[int] = None
    available_slots: Optional[int] = 0
    max_slots: Optional[int] = 0
    price: Optional[Money] = None
    price_per_extra_player: Optional[int] = None
    notes: Optional[str] = None
    is_prime_time: bool = False
    category: Optional[TeeTimeCategory] = None
    space: Optional[Space] = None
    course: Optional[TeeTimeCourse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    players: Optional[int] = None

    class Config:
        populate_by_name = True

    @property
    def time_display(self) -> str:
        """Get formatted time for display in Stockholm timezone."""
        if self.from_time:
            # Convert to Stockholm time if needed
            stockholm_tz = ZoneInfo("Europe/Stockholm")
            if self.from_time.tzinfo:
                local_time = self.from_time.astimezone(stockholm_tz)
            else:
                # Assume UTC if no timezone info
                local_time = self.from_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(
                    stockholm_tz
                )
            return local_time.strftime("%H:%M")
        return "N/A"

    @property
    def is_available(self) -> bool:
        """Check if the tee time has available slots."""
        return (self.available_slots or 0) > 0

    @property
    def price_display(self) -> str:
        """Get formatted price for display."""
        if self.price and self.price.formatted:
            return self.price.formatted
        elif self.price and self.price.amount:
            return f"{self.price.amount} {self.price.currency or 'SEK'}"
        return "N/A"


class TeeTimeAvailabilityView(BaseModel):
    """Simple availability view from the API."""

    uuid: str
    is_available: bool
    type: Optional[str] = Field(alias="@type", default=None)
    id: Optional[str] = Field(alias="@id", default=None)

    class Config:
        populate_by_name = True


class TeeTimeAvailabilityResponse(BaseModel):
    """Response from the availability API."""

    tee_times: List[TeeTime] = Field(default_factory=list)
    total_count: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None
