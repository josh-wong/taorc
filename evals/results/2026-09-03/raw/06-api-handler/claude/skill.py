```python
"""Booking creation endpoint.

There is no framework or database behind this module: `request` is anything
with a `.json` dict, and persistence is a stub (see `_store_booking`).
"""

from datetime import datetime, timedelta

# Sample inventory. A real deployment would load this from the room service.
KNOWN_ROOMS = {"oak-1", "birch-2", "cedar-3"}

MAX_BOOKING_HOURS = 4

_REQUIRED_FIELDS = ("room_id", "start", "end")


def create_booking(request):
    """Create a booking from `request.json` and return `(status_code, body)`.

    Success is `(201, {"room_id", "start", "end"})`, where `start` and `end`
    are the parsed times re-serialized to ISO 8601, so the caller sees what
    was stored rather than what it sent.

    Failures return `(status, {"error": <reason>})`:
      400 -- a required field is missing, `room_id` is not a string, a
             timestamp is not valid ISO 8601, only one timestamp carries a
             UTC offset, or `end` is not strictly after `start`
      404 -- `room_id` is well-formed but not in KNOWN_ROOMS
      422 -- the booking is longer than MAX_BOOKING_HOURS

    Checks run in that order deliberately. A request with a malformed `start`
    and an unknown room gets the 400: the client has to fix the malformed
    field before the room lookup tells it anything useful.
    """
    payload = request.json

    missing_fields = [name for name in _REQUIRED_FIELDS if name not in payload]
    if missing_fields:
        return 400, {
            "error": f"Missing required field(s): {', '.join(missing_fields)}"
        }

    room_id = payload["room_id"]
    if not isinstance(room_id, str):
        return 400, {"error": "room_id must be a string"}

    start = _parse_iso8601(payload["start"])
    if start is None:
        return 400, {
            "error": "start must be an ISO 8601 datetime, e.g. 2024-03-01T09:00:00"
        }

    end = _parse_iso8601(payload["end"])
    if end is None:
        return 400, {
            "error": "end must be an ISO 8601 datetime, e.g. 2024-03-01T11:30:00"
        }

    # Comparing or subtracting a naive datetime and an aware one raises
    # TypeError, so reject the mix here rather than crashing three lines down.
    if (start.tzinfo is None) != (end.tzinfo is None):
        return 400, {
            "error": "start and end must both include a UTC offset, or both omit one"
        }

    if end <= start:
        return 400, {"error": "end must be after start"}

    if room_id not in KNOWN_ROOMS:
        return 404, {"error": f"Unknown room: {room_id}"}

    if end - start > timedelta(hours=MAX_BOOKING_HOURS):
        return 422, {"error": f"A booking may not exceed {MAX_BOOKING_HOURS} hours"}

    _store_booking(room_id, start, end)
    return 201, {
        "room_id": room_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _parse_iso8601(value):
    """Return the datetime `value` denotes, or None if it is not one.

    Returns None instead of raising because both callers turn a parse failure
    into a 400, and a bad client payload is not exceptional here.

    Before Python 3.11, `fromisoformat` rejects a trailing "Z", so
    "2024-03-01T09:00:00Z" parses on 3.11+ and is a 400 on older runtimes.
    """
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _store_booking(room_id, start, end):
    """Stub for the persistence call. Accepts everything and stores nothing."""
```

**What I deliberately left out**

- **No type check on `request.json` itself.** You specified it is a dict, so a defensive `isinstance` guard would be noise on a contract you already stated. If untrusted input can reach this, that check belongs in the framework layer, not here.
- **No double-booking / overlap check.** Not in the spec, and it needs the storage layer that does not exist yet. Adding it would mean inventing a query interface no caller asked for (`S6`).
- **No timezone normalization to UTC.** The endpoint rejects mixed-awareness input rather than guessing a zone for a naive timestamp. Which policy you want is a product decision, not a readability one.
- **Two explicit parse-and-check blocks instead of a loop over `("start", "end")`.** The loop would be shorter but would add a dict accumulator and an unpack; the repetition here is four lines a stranger reads without stopping (`P2`).
- **No tests.** Say the word and I will add cases for each status code, the `end == start` boundary, and the mixed-offset path.

**Verification**: I found no `scripts/taorc_lint.py` in this environment, so step 4 was skipped rather than substituted with a guess.