## `bookings.py`

```python
"""Booking creation endpoint."""

from datetime import datetime, timedelta

KNOWN_ROOMS = {"oak-101", "birch-204", "cedar-305"}

MAX_BOOKING_HOURS = 4

# Stands in for the bookings table. Replace with the real repository.
_SAVED_BOOKINGS = []


class _InvalidField(Exception):
    """A required field is missing or unusable. The message is caller-facing."""


def create_booking(request):
    """Create a booking from `request.json`.

    Returns a (status_code, body) tuple. On success the status is 201 and the
    body echoes the booking with both timestamps normalized by
    `datetime.isoformat`, so they may differ textually from the input.

    Failures return a body of the form {"error": <caller-facing reason>}:

    400  body is not an object, a required field is missing or of the wrong
         type, a timestamp is not ISO 8601, `end` is not strictly after
         `start`, or exactly one of the two timestamps carries a UTC offset
    404  `room_id` is a well-formed string but not in KNOWN_ROOMS
    422  the booking is valid but longer than MAX_BOOKING_HOURS

    A zero-length booking is rejected as 400, not 422, because `end` must be
    strictly after `start`.
    """
    try:
        room_id, start, end = _read_booking_fields(request.json)
    except _InvalidField as invalid:
        return 400, {"error": str(invalid)}

    if room_id not in KNOWN_ROOMS:
        return 404, {"error": f"Unknown room: {room_id!r}."}

    if end - start > timedelta(hours=MAX_BOOKING_HOURS):
        return 422, {
            "error": f"Booking exceeds the {MAX_BOOKING_HOURS}-hour maximum."
        }

    _SAVED_BOOKINGS.append((room_id, start, end))
    return 201, {
        "room_id": room_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _read_booking_fields(payload):
    """Return (room_id, start, end), or raise _InvalidField with the reason."""
    if not isinstance(payload, dict):
        return _reject("Request body must be a JSON object.")

    room_id = payload.get("room_id")
    if room_id is None:
        return _reject("Missing required field: room_id.")
    if not isinstance(room_id, str) or not room_id.strip():
        return _reject("Field room_id must be a non-empty string.")

    start = _read_timestamp(payload, "start")
    end = _read_timestamp(payload, "end")

    # Comparing an aware datetime to a naive one raises TypeError, so reject
    # the mismatch here rather than letting it surface as a 500 below.
    if (start.tzinfo is None) != (end.tzinfo is None):
        return _reject(
            "Fields start and end must both include a UTC offset, or both omit it."
        )

    if end <= start:
        return _reject("Field end must be later than start.")

    return room_id.strip(), start, end


def _read_timestamp(payload, field):
    """Parse one ISO 8601 field, or raise _InvalidField with the reason."""
    value = payload.get(field)
    if value is None:
        return _reject(f"Missing required field: {field}.")
    if not isinstance(value, str):
        return _reject(f"Field {field} must be an ISO 8601 datetime string.")

    try:
        # Before Python 3.11 this rejects a trailing "Z"; clients must send a
        # numeric offset such as "+00:00" on older runtimes.
        return datetime.fromisoformat(value)
    except ValueError:
        return _reject(f"Field {field} is not a valid ISO 8601 datetime: {value!r}.")


def _reject(reason):
    raise _InvalidField(reason) from None
```

## Notes on the shape

**Why the exception.** The three status codes have different causes, and field
validation produces roughly a dozen distinct messages. Returning
`(fields, error)` pairs from `_read_booking_fields` would force an error check
after every parse and push nesting past two levels (`F6`). A private exception
caught in one place at the top of the handler keeps the handler body a flat
sequence of guard clauses (`F5`) and keeps the validator readable as a
straight-line list of rejections.

`_reject` exists so each rejection reads as one statement at the point of the
check rather than a `raise` that visually interrupts the sequence. It is typed
as returning a value only so callers can write `return _reject(...)`; it never
returns.

**Constant with the unit in the name.** `MAX_BOOKING_HOURS = 4` rather than a
`timedelta` constant, because the number appears in the caller-facing message
(`N3`, `N13`). A `timedelta(hours=4)` renders as `4:00:00` in an f-string, which
is not what you want a client to read.

**The two comments that are not restatements.** Both record something the code
cannot say: that the `tzinfo` guard is preventing a `TypeError` that would
otherwise escape as a 500, and that `fromisoformat` has a version-dependent
pitfall around `"Z"` (`C6`, `C7`). Everything else in the file is named well
enough not to need one.

**Docstring corner cases.** The handler docstring states what a zero-length
booking does, because the 400-versus-422 boundary is exactly the question a
caller will have and the code answers it only by ordering (`C14`).

## What I deliberately left alone

- **No framework integration.** No decorator, blueprint, or route registration, since no framework was named. `create_booking` is a plain function you can wire up or call directly from a test.
- **`_SAVED_BOOKINGS` is a list, not a real store.** It does no overlap detection, no capacity check, and no deduplication. A real implementation would need a conflict path — likely 409 — and that path is not in the spec.
- **No timezone normalization.** Naive input stays naive, and an offset is preserved as sent. Coercing everything to UTC is a policy decision, not a readability one (`X4`).
- **`room_id` is stripped on the way out but matched unstripped against `KNOWN_ROOMS`** — actually matched after stripping, since `_read_booking_fields` returns the stripped value. I did not add case folding; `"OAK-101"` will 404. Say the word if IDs should match case-insensitively.
- **No logging.** Nothing here logs the rejected payloads, which a production handler probably should.