Write a handler function `create_booking(request)` for a hypothetical web
framework where `request.json` is a dict and the function returns a
`(status_code, body_dict)` tuple. Behavior:

- Required fields: `room_id` (str), `start` and `end` (ISO 8601 datetime
  strings, `end` after `start`).
- Missing or malformed required fields: `400` with `{"error": "..."}`
  describing the problem.
- `room_id` not in `KNOWN_ROOMS` (a module-level set you define with a few
  sample IDs): `404` with `{"error": "..."}`.
- Booking duration over 4 hours: `422` with `{"error": "..."}`.
- Otherwise: `201` with `{"room_id": ..., "start": ..., "end": ...}`.

No real framework or database is available — stub anything you'd otherwise
call out to.
