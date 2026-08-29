```python
from datetime import datetime, timezone, timedelta

# Sample known rooms for validation
KNOWN_ROOMS = {
    "room-alpha",
    "room-beta",
    "room-gamma",
}


def parse_iso8601_utc(datetimeText: str) -> datetime:
    """
    Parse an ISO 8601 datetime string into an aware UTC datetime.

    Accepts strings with or without timezone info. Naive datetimes are
    treated as UTC.
    """
    try:
        parsed = datetime.fromisoformat(datetimeText)
    except (TypeError, ValueError):
        raise ValueError("Invalid ISO 8601 datetime")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def create_booking(request):
    body = request.json or {}

    roomId = body.get("room_id")
    startText = body.get("start")
    endText = body.get("end")

    if not isinstance(roomId, str) or not roomId:
        return 400, {"error": "Missing or invalid 'room_id' (expected non-empty string)"}

    if not isinstance(startText, str) or not startText:
        return 400, {"error": "Missing or invalid 'start' (expected ISO 8601 string)"}

    if not isinstance(endText, str) or not endText:
        return 400, {"error": "Missing or invalid 'end' (expected ISO 8601 string)"}

    try:
        startTime = parse_iso8601_utc(startText)
    except ValueError:
        return 400, {"error": "Malformed 'start' (expected ISO 8601 datetime)"}

    try:
        endTime = parse_iso8601_utc(endText)
    except ValueError:
        return 400, {"error": "Malformed 'end' (expected ISO 8601 datetime)"}

    if endTime <= startTime:
        return 400, {"error": "'end' must be after 'start'"}

    if roomId not in KNOWN_ROOMS:
        return 404, {"error": f"Unknown room_id '{roomId}'"}

    bookingDuration = endTime - startTime
    maxDuration = timedelta(hours=4)

    if bookingDuration > maxDuration:
        return 422, {"error": "Booking duration cannot exceed 4 hours"}

    # Stubbed persistence: in a real system, this is where we'd write to a DB
    # and possibly return a booking ID.

    return 201, {
        "room_id": roomId,
        "start": startTime.isoformat(),
        "end": endTime.isoformat(),
    }
```