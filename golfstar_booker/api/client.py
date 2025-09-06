"""API client for Sweetspot/Golfstar API."""

import httpx
from typing import List, Optional, Dict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging

from ..models.course import Course
from ..models.teetime import TeeTime, Money, TeeTimeCourse


logger = logging.getLogger(__name__)


def is_competition_time(tee_time_data: dict) -> bool:
    """Check if a tee time is a competition based on API response data.

    Competition times are identified by:
    - Having a category with description containing "Tävling bokad av" (Competition booked by)
    - Or having a category with custom_name "Tävling" (Competition)
    """
    category = tee_time_data.get("category", {})
    if not category:
        return False

    # Check for competition indicators in the category
    description = category.get("description", "").lower()
    custom_name = category.get("custom_name", "").lower()

    # Check if this is a competition (tävling in Swedish)
    if "tävling" in description or "tävling" in custom_name:
        logger.debug(f"Found competition time with category: {category}")
        return True

    return False


class GolfstarAPIClient:
    """Client for interacting with the Golfstar/Sweetspot API."""

    BASE_URL = "https://middleware.sweetspot.io/api"
    GOLFSTAR_CLUB_ID = "275"  # Golfstar Sverige club ID

    def __init__(self, timeout: float = 30.0, auth_token: Optional[str] = None):
        """Initialize the API client.

        Args:
            timeout: Request timeout in seconds
            auth_token: Optional JWT authorization token
        """
        self.auth_token = auth_token
        self.client = httpx.Client(
            base_url=self.BASE_URL, timeout=timeout, headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        headers = {
            "x-application-origin": "WB",
            "accept": "*/*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "origin": "https://book.sweetspot.io",
            "referer": "https://book.sweetspot.io/",
        }
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"
        return headers

    def get_courses(
        self,
        club_id: Optional[str] = None,
        order_by: str = "name",
        order_direction: str = "asc",
        search: Optional[str] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
    ) -> List[Course]:
        """Get list of courses for a club.

        Args:
            club_id: Club ID to filter by (defaults to Golfstar)
            order_by: Field to order by (e.g., "name", "id")
            order_direction: Order direction ("asc" or "desc")
            search: Search term to filter courses
            limit: Number of items per page
            page: Page number

        Returns:
            List of Course objects
        """
        if club_id is None:
            club_id = self.GOLFSTAR_CLUB_ID

        params = {"club.id": club_id, f"order[{order_by}]": order_direction}

        if search:
            params["search"] = search
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page

        try:
            response = self.client.get("/courses", params=params)
            response.raise_for_status()

            courses_data = response.json()
            return [Course(**course_data) for course_data in courses_data]

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching courses: {e}")
            raise

    def get_available_times(
        self,
        course_uuids: List[str],
        start_datetime: datetime,
        end_datetime: datetime,
        players: int = 1,
        limit: int = 100,
        page: int = 1,
    ) -> List[TeeTime]:
        """Get available tee times for courses.

        Args:
            course_uuids: List of course UUIDs to check
            start_datetime: Start datetime for availability search
            end_datetime: End datetime for availability search
            players: Minimum number of available slots
            limit: Number of results per page
            page: Page number

        Returns:
            List of TeeTime objects
        """
        # For now, we'll use the regular tee-times endpoint instead of availability
        # The availability endpoint only returns boolean flags, not full details

        # Convert datetimes to UTC for API
        # If timezone-aware, convert to UTC; if naive, assume UTC
        if start_datetime.tzinfo:
            start_utc = start_datetime.astimezone(timezone.utc)
            start_iso = start_utc.isoformat().replace("+00:00", "Z")
        else:
            start_iso = start_datetime.isoformat() + "Z"

        if end_datetime.tzinfo:
            end_utc = end_datetime.astimezone(timezone.utc)
            end_iso = end_utc.isoformat().replace("+00:00", "Z")
        else:
            end_iso = end_datetime.isoformat() + "Z"

        all_tee_times = []

        # Query each course separately for now
        for course_uuid in course_uuids:
            params = {
                "from[after]": start_iso,
                "from[before]": end_iso,
                "course.uuid": course_uuid,
                "available_slots[gte]": players,
                "limit": limit,
                "page": page,
                "order[from]": "asc",
            }

            try:
                response = self.client.get("/tee-times", params=params)
                response.raise_for_status()

                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    items = data
                else:
                    # Handle paginated response
                    items = data.get("hydra:member", data.get("items", []))

                # Parse each tee time
                for item in items:
                    try:
                        # Only process if it has enough available slots for the requested number of players
                        available_slots = item.get("available_slots", 0)
                        if available_slots >= players:
                            # Map course info if available
                            if "course" in item and isinstance(item["course"], dict):
                                course_info = TeeTimeCourse(
                                    id=item["course"].get("id", 0),
                                    uuid=item["course"].get(
                                        "uuid", course_uuid
                                    ),  # Use the UUID we're querying
                                    name=item["course"].get("name", ""),
                                    club_name=item["course"]
                                    .get("club", {})
                                    .get("name", "")
                                    if "club" in item["course"]
                                    else "",
                                )
                                item["course"] = course_info
                            else:
                                # If no course info in response, create minimal info with UUID
                                item["course"] = TeeTimeCourse(
                                    id=0, uuid=course_uuid, name="", club_name=""
                                )

                            # Parse money if it's a dict
                            if "price" in item and isinstance(item["price"], dict):
                                item["price"] = Money(**item["price"])

                            # Check if this is a competition time before creating TeeTime
                            if not is_competition_time(item):
                                # Create the TeeTime object
                                all_tee_times.append(TeeTime(**item))
                            else:
                                logger.debug(f"Skipping competition time: {item}")
                    except Exception as e:
                        logger.warning(f"Failed to parse tee time: {e}")
                        continue

            except httpx.HTTPError as e:
                # Log error but continue with other courses
                logger.error(f"HTTP error for course {course_uuid}: {e}")
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response body: {e.response.text}")
                # Don't raise, continue with other courses
            except Exception as e:
                logger.error(f"Error fetching times for course {course_uuid}: {e}")
                # Don't raise, continue with other courses

        # Sort all tee times by datetime
        all_tee_times.sort(key=lambda t: t.from_time)

        return all_tee_times

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
