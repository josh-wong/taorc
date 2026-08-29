## `bookings.py`

```python
"""Booking creation endpoint and the validation it runs before storage."""

from datetime import datetime, timedelta

KNOWN_ROOMS = {"oak-101", "birch-202", "cedar-303"}

MAX_BOOKING_HOURS = 4
MAX_BOOKING_DURATION = timedelta(hours=MAX_BOOKING_HOURS)


def create_booking(request):
    """Create a booking from request.json, returning (status_code, body).

    Checks run in a fixed order and stop at the first failure, so a request
    that is wrong in several ways reports only one problem: malformed fields
    (400), then unknown room (404), then over-long duration (422).

    The 201 body echoes the timestamps in normalized ISO 8601 form, which may
    differ textually from what the caller sent (`...Z` becomes `...+00:00`).
    """
    error, booking = _parse_booking_fields(request.json)
    if error is not None:
        return 400, {"error": error}

    room_id, start, end = booking

    if room_id not in KNOWN_ROOMS:
        return 404, {"error": f"Unknown room_id: {room_id!r}."}

    if end - start > MAX_BOOKING_DURATION:
        return 422, {
            "error": f"A booking may last at most {MAX_BOOKING_HOURS} hours."
        }

    _save_booking(room_id, start, end)
    return 201, {
        "room_id": room_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _parse_booking_fields(payload):
    """Validate the required fields, returning (error_message, booking).

    On success the error is None and booking is a (room_id, start, end) tuple
    with end strictly after start. On failure booking is None and the error
    describes the first problem found, phrased for the client.
    """
    if not isinstance(payload, dict):
        return "Request body must be a JSON object.", None

    missing = [
        field for field in ("room_id", "start", "end") if field not in payload
    ]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}.", None

    room_id = payload["room_id"]
    if not isinstance(room_id, str) or not room_id.strip():
        return "room_id must be a non-empty string.", None

    start_error, start = _parse_iso_datetime(payload["start"], "start")
    if start_error is not None:
        return start_error, None

    end_error, end = _parse_iso_datetime(payload["end"], "end")
    if end_error is not None:
        return end_error, None

    # Comparing or subtracting a naive datetime and an aware one raises
    # TypeError, so reject the mix here rather than 500-ing below.
    if (start.tzinfo is None) != (end.tzinfo is None):
        return "start and end must both specify a UTC offset, or neither.", None

    if end <= start:
        return "end must be after start.", None

    return None, (room_id, start, end)


def _parse_iso_datetime(raw_value, field_name):
    """Return (error_message, parsed_datetime) for one ISO 8601 string field."""
    if not isinstance(raw_value, str):
        return f"{field_name} must be an ISO 8601 datetime string.", None

    # fromisoformat only accepts a trailing "Z" from Python 3.11 onward.
    if raw_value.endswith("Z"):
        raw_value = raw_value[:-1] + "+00:00"

    try:
        return None, datetime.fromisoformat(raw_value)
    except ValueError:
        return f"{field_name} is not a valid ISO 8601 datetime.", None


def _save_booking(room_id, start, end):
    """Stub for persistence: a real version would insert a row and return its ID."""
```

## Notes on the shape

- Both helpers return `(error, value)` in that order, so the call sites read the
  same way (`A4`). Mixing `(value, error)` in one of them would cost a reader a
  double take.
- `MAX_BOOKING_HOURS` is the named constant and `MAX_BOOKING_DURATION` is derived
  from it, so the error message and the comparison cannot drift apart, and the
  message says "4 hours" rather than `timedelta`'s `4:00:00` (`N3`, `N13`).
- The mixed naive/aware check exists because `end <= start` would otherwise raise
  `TypeError` on `{"start": "2024-01-01T09:00:00", "end": "2024-01-01T10:00:00Z"}` —
  a 500 for what is really a client error. The comment records the *why*, since
  the line itself looks arbitrary (`C6`).
- Validation is a separate function from dispatch so each is describable in one
  sentence (`S1`, `S3`); `create_booking` then reads as five guard clauses with no
  nesting (`F5`, `F6`).

## What I did not do

- **No tests.** You did not ask for them, so adding a test module would have
  widened the diff (`X1`). Say the word and I will add cases for each status code
  plus the naive/aware mix.
- **No `Booking` dataclass.** A three-element tuple unpacked at one call site does
  not yet justify a type (`S6`). A second consumer of the parsed fields would
  change that.
- **No request-body size or unknown-field rejection.** Not in the spec, and
  guessing at policy here would be inventing a requirement.
- **Linter not run.** I found no `scripts/taorc_lint.py` under any of the skill
  roots in this context, so I skipped the verify step rather than installing one.