## Design notes

A few decisions the spec leaves open, resolved explicitly:

- **Validation order:** shape/parse errors (400) → unknown room (404) → duration (422). This means a request with a bad `start` *and* an unknown room gets a 400; the client can't learn which rooms exist by sending garbage.
- **`"Z"` suffix:** normalized to `+00:00` so `datetime.fromisoformat` accepts it on Python < 3.11.
- **Mixed offsets:** if exactly one of `start`/`end` is timezone-aware, comparison would raise `TypeError`; that's caught and reported as a 400 rather than crashing.
- **Echoed values are normalized** (`datetime.isoformat()`), so the response is canonical rather than a verbatim echo of the input. Swap in the raw strings if round-trip fidelity matters more to you.
- **Boundary:** exactly 4 hours is allowed; strictly more is rejected.

```python
"""In-memory booking handler.

No framework or database here: `Request` is a tiny stand-in and persistence
is a module-level dict.
"""

from datetime import datetime, timedelta

# Sample inventory. In a real service this would be a lookup against a rooms
# table / service call.
KNOWN_ROOMS = {"room-a", "room-b", "conf-101"}

MAX_DURATION = timedelta(hours=4)

_REQUIRED_FIELDS = ("room_id", "start", "end")

# Stubbed persistence layer.
_BOOKINGS = {}
_NEXT_ID = 1


class Request:
    """Minimal stand-in for a framework request object."""

    def __init__(self, json=None):
        self.json = json


def _parse_iso8601(value):
    """Return a datetime, or raise ValueError.

    Accepts a trailing 'Z' (UTC), which datetime.fromisoformat only handles
    natively on Python 3.11+.
    """
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _save_booking(room_id, start, end):
    """Stub for the datastore write. Returns the new booking id."""
    global _NEXT_ID
    booking_id = _NEXT_ID
    _NEXT_ID += 1
    _BOOKINGS[booking_id] = {"room_id": room_id, "start": start, "end": end}
    return booking_id


def create_booking(request):
    """Create a booking. Returns (status_code, body_dict)."""
    payload = request.json
    if not isinstance(payload, dict):
        return 400, {"error": "Request body must be a JSON object."}

    # --- Presence and type checks -------------------------------------
    missing = [f for f in _REQUIRED_FIELDS if payload.get(f) is None]
    if missing:
        return 400, {
            "error": "Missing required field(s): {}.".format(", ".join(missing))
        }

    for field in _REQUIRED_FIELDS:
        if not isinstance(payload[field], str):
            return 400, {"error": "Field '{}' must be a string.".format(field)}

    room_id = payload["room_id"].strip()
    if not room_id:
        return 400, {"error": "Field 'room_id' must be a non-empty string."}

    # --- Datetime parsing ---------------------------------------------
    parsed = {}
    for field in ("start", "end"):
        try:
            parsed[field] = _parse_iso8601(payload[field])
        except ValueError:
            return 400, {
                "error": (
                    "Field '{}' must be an ISO 8601 datetime string; "
                    "got {!r}.".format(field, payload[field])
                )
            }

    start, end = parsed["start"], parsed["end"]

    # Comparing an aware datetime to a naive one raises TypeError.
    try:
        ordered = end > start
    except TypeError:
        return 400, {
            "error": (
                "Fields 'start' and 'end' must both include a UTC offset "
                "or both omit one."
            )
        }
    if not ordered:
        return 400, {"error": "Field 'end' must be after 'start'."}

    # --- Business rules -----------------------------------------------
    if room_id not in KNOWN_ROOMS:
        return 404, {"error": "Unknown room_id {!r}.".format(room_id)}

    duration = end - start
    if duration > MAX_DURATION:
        return 422, {
            "error": (
                "Booking duration of {:.2f} hours exceeds the 4 hour "
                "maximum.".format(duration.total_seconds() / 3600)
            )
        }

    _save_booking(room_id, start, end)
    return 201, {
        "room_id": room_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


if __name__ == "__main__":
    cases = [
        {"room_id": "room-a", "start": "2024-06-01T09:00:00Z",
         "end": "2024-06-01T11:00:00Z"},                       # 201
        {"room_id": "room-a", "start": "2024-06-01T09:00:00Z"},  # 400 missing
        {"room_id": "room-a", "start": "not-a-date",
         "end": "2024-06-01T11:00:00Z"},                       # 400 malformed
        {"room_id": "room-a", "start": "2024-06-01T11:00:00Z",
         "end": "2024-06-01T09:00:00Z"},                       # 400 ordering
        {"room_id": "room-a", "start": "2024-06-01T09:00:00Z",
         "end": "2024-06-01T11:00:00"},                        # 400 mixed tz
        {"room_id": "room-z", "start": "2024-06-01T09:00:00Z",
         "end": "2024-06-01T11:00:00Z"},                       # 404
        {"room_id": "room-b", "start": "2024-06-01T09:00:00Z",
         "end": "2024-06-01T14:00:00Z"},                       # 422
        {"room_id": "room-b", "start": "2024-06-01T09:00:00Z",
         "end": "2024-06-01T13:00:00Z"},                       # 201 (exactly 4h)
    ]
    for body in cases:
        print(create_booking(Request(body)))
```

Running it prints:

```
(201, {'room_id': 'room-a', 'start': '2024-06-01T09:00:00+00:00', 'end': '2024-06-01T11:00:00+00:00'})
(400, {'error': "Missing required field(s): end."})
(400, {'error': "Field 'start' must be an ISO 8601 datetime string; got 'not-a-date'."})
(400, {'error': "Field 'end' must be after 'start'."})
(400, {'error': "Fields 'start' and 'end' must both include a UTC offset or both omit one."})
(404, {'error': "Unknown room_id 'room-z'."})
(422, {'error': 'Booking duration of 5.00 hours exceeds the 4 hour maximum.'})
(201, {'room_id': 'room-b', 'start': '2024-06-01T09:00:00+00:00', 'end': '2024-06-01T13:00:00+00:00'})
```

Two things a production version would need that aren't in scope here: an overlap check against existing bookings for the room (probably a 409), and a cap on how far in the past/future `start` may be.