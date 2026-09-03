```python
from datetime import datetime, timedelta, timezone

# Sample known rooms
KNOWN_ROOMS = {"room-101", "room-202", "conference-a", "conference-b"}


def _parse_iso8601(dt_str):
    """
    Parse an ISO 8601 datetime string into an aware datetime (UTC if no tz).
    Accepts strings like:
      - "2024-08-29T10:00:00"
      - "2024-08-29T10:00:00Z"
      - "2024-08-29T10:00:00+02:00"
    Returns a datetime or raises ValueError.
    """
    if not isinstance(dt_str, str):
        raise ValueError("Datetime value must be a string")

    # Handle trailing 'Z' as UTC
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"

    dt = datetime.fromisoformat(dt_str)

    # Make naive datetimes UTC-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def create_booking(request):
    data = getattr(request, "json", None)
    if not isinstance(data, dict):
        return 400, {"error": "Request body must be a JSON object"}

    # Validate presence and type of room_id
    room_id = data.get("room_id")
    if room_id is None:
        return 400, {"error": "Missing required field: room_id"}
    if not isinstance(room_id, str) or not room_id.strip():
        return 400, {"error": "Field 'room_id' must be a non-empty string"}

    # Validate presence of start and end
    start_raw = data.get("start")
    end_raw = data.get("end")

    if start_raw is None:
        return 400, {"error": "Missing required field: start"}
    if end_raw is None:
        return 400, {"error": "Missing required field: end"}

    # Parse datetimes
    try:
        start_dt = _parse_iso8601(start_raw)
    except Exception:
        return 400, {"error": "Field 'start' must be a valid ISO 8601 datetime string"}

    try:
        end_dt = _parse_iso8601(end_raw)
    except Exception:
        return 400, {"error": "Field 'end' must be a valid ISO 8601 datetime string"}

    # Validate ordering
    if end_dt <= start_dt:
        return 400, {"error": "Field 'end' must be after 'start'"}

    # Validate room existence
    if room_id not in KNOWN_ROOMS:
        return 404, {"error": f"Room '{room_id}' not found"}

    # Validate duration (max 4 hours)
    duration = end_dt - start_dt
    if duration > timedelta(hours=4):
        return 422, {"error": "Booking duration cannot exceed 4 hours"}

    # Stub: here you would persist the booking to a database, etc.

    # Return created booking (echoing original strings)
    return 201, {
        "room_id": room_id,
        "start": start_raw,
        "end": end_raw,
    }
```