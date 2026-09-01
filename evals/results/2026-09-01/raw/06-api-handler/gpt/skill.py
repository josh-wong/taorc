```python
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

# Sample known rooms for validation
KNOWN_ROOMS = {"room-101", "room-202", "room-303"}


def parse_iso8601(timestampText: Any) -> datetime:
    """
    Parse an ISO 8601 datetime string using datetime.fromisoformat.

    Returns:
        A datetime object.

    Raises:
        ValueError: If timestampText is not a string or not a valid ISO 8601 value.
    """
    if not isinstance(timestampText, str):
        raise ValueError("Timestamp must be a string")
    # fromisoformat is lenient but good enough for this example
    return datetime.fromisoformat(timestampText)


def create_booking(request) -> Tuple[int, Dict[str, Any]]:
    """
    Create a booking from request.json.

    Returns:
        (400, {"error": ...}) for missing/malformed fields.
        (404, {"error": ...}) if room_id is unknown.
        (422, {"error": ...}) if duration exceeds 4 hours.
        (201, {"room_id": ..., "start": ..., "end": ...}) on success.

    On empty or non-dict request.json, treats it as missing required fields.
    Never raises on validation errors; always returns an error response instead.
    """
    payload = getattr(request, "json", None)
    if not isinstance(payload, dict):
        return 400, {"error": "Request body must be a JSON object"}

    roomId = payload.get("room_id")
    startText = payload.get("start")
    endText = payload.get("end")

    if roomId is None:
        return 400, {"error": "Missing required field: room_id"}
    if startText is None:
        return 400, {"error": "Missing required field: start"}
    if endText is None:
        return 400, {"error": "Missing required field: end"}

    if not isinstance(roomId, str):
        return 400, {"error": "room_id must be a string"}

    try:
        startTime = parse_iso8601(startText)
    except ValueError:
        return 400, {"error": "start must be a valid ISO 8601 datetime string"}

    try:
        endTime = parse_iso8601(endText)
    except ValueError:
        return 400, {"error": "end must be a valid ISO 8601 datetime string"}

    if endTime <= startTime:
        return 400, {"error": "end must be after start"}

    if roomId not in KNOWN_ROOMS:
        return 404, {"error": f"Unknown room_id: {roomId}"}

    bookingDuration = endTime - startTime
    maxDuration = timedelta(hours=4)
    if bookingDuration > maxDuration:
        return 422, {"error": "Booking duration cannot exceed 4 hours"}

    # In a real app, this is where we'd persist the booking.
    # For this stub, we just echo the validated fields.
    return 201, {
        "room_id": roomId,
        "start": startTime.isoformat(),
        "end": endTime.isoformat(),
    }
```