```python
KNOWN_ROOMS = {"room_001", "room_002", "room_003"}


def create_booking(request: dict) -> tuple[int, dict]:
    """Create a new booking from request data."""

    # Validate required fields exist and are valid types
    if not _validate_required_fields(request):
        return (400, {"error": "Missing or malformed required fields"})

    room_id = request["room_id"]
    start_str = request["start"]
    end_str = request["end"]

    # Check room exists in known rooms
    if room_id not in KNOWN_ROOMS:
        return (404, {"error": f"Room {room_id} not found"})

    # Parse ISO 8601 datetime strings and validate ordering
    start_dt = _parse_iso_datetime(start_str)
    end_dt = _parse_iso_datetime(end_str)

    if start_dt >= end_dt:
        return (400, {"error": "Start time must be before end time"})

    # Validate booking duration is within 4-hour limit
    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    if duration_hours > 4:
        return (422, {"error": "Booking duration exceeds 4 hours"})

    # Return successful booking with room and time details
    return (201, {
        "room_id": room_id,
        "start": start_str,
        "end": end_str,
    })


def _validate_required_fields(request: dict) -> bool:
    """Check that required fields exist with correct types."""
    if not isinstance(request, dict):
        return False

    required = {"room_id", "start", "end"}
    missing = required - set(request.keys())
    if missing:
        return False

    if not isinstance(request["room_id"], str):
        return False
    if not isinstance(request["start"], str) or not request["start"].startswith("20"):
        return False
    if not isinstance(request["end"], str) or not request["end"].startswith("20"):
        return False

    return True


def _parse_iso_datetime(date_str: str) -> datetime.datetime:
    """Parse ISO 8601 datetime string to datetime object."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Invalid ISO 8601 format: {date_str}")
```