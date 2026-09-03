```python
from datetime import datetime, timezone, timedelta

# Sample known rooms for validation
KNOWN_ROOMS = {"room-101", "room-202", "room-303"}


def parse_iso8601_utc(datetimeText):
    """
    Parse an ISO 8601 datetime string into an aware UTC datetime.

    Accepts a trailing 'Z' as UTC or an explicit offset.
    Returns None if parsing fails.
    """
    if not isinstance(datetimeText, str):
        return None

    # Handle common "Z" UTC suffix
    if datetimeText.endswith("Z"):
        datetimeText = datetimeText[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(datetimeText)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        # Treat naive datetimes as UTC for this handler
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed


def create_booking(request):
    """
    Create a booking from request.json.

    Returns:
      - (400, {"error": ...}) for missing or malformed required fields.
      - (404, {"error": ...}) when room_id is unknown.
      - (422, {"error": ...}) when duration exceeds 4 hours.
      - (201, {"room_id": ..., "start": ..., "end": ...}) on success.

    On any error, the body contains a single "error" message.
    """
    payload = getattr(request, "json", None)
    if not isinstance(payload, dict):
        return 400, {"error": "Request body must be a JSON object."}

    roomId = payload.get("room_id")
    startText = payload.get("start")
    endText = payload.get("end")

    if not isinstance(roomId, str) or not roomId:
        return 400, {"error": "Field 'room_id' is required and must be a non-empty string."}

    if not isinstance(startText, str) or not startText:
        return 400, {"error": "Field 'start' is required and must be an ISO 8601 datetime string."}

    if not isinstance(endText, str) or not endText:
        return 400, {"error": "Field 'end' is required and must be an ISO 8601 datetime string."}

    startAt = parse_iso8601_utc(startText)
    if startAt is None:
        return 400, {"error": "Field 'start' must be a valid ISO 8601 datetime."}

    endAt = parse_iso8601_utc(endText)
    if endAt is None:
        return 400, {"error": "Field 'end' must be a valid ISO 8601 datetime."}

    if endAt <= startAt:
        return 400, {"error": "Field 'end' must be after 'start'."}

    if roomId not in KNOWN_ROOMS:
        return 404, {"error": f"Room '{roomId}' was not found."}

    bookingDuration = endAt - startAt
    maxDuration = timedelta(hours=4)
    if bookingDuration > maxDuration:
        return 422, {"error": "Booking duration cannot exceed 4 hours."}

    # Stub for persistence or other side effects would go here.

    return 201, {
        "room_id": roomId,
        "start": startText,
        "end": endText,
    }
```