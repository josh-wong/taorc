```python
from datetime import datetime, timedelta
from typing import Dict, Tuple, Any

# Module-level set of known room IDs
KNOWN_ROOMS = {"room_001", "room_002", "room_003", "room_004"}


def create_booking(request: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Handler function for creating a new booking.

    Args:
        request: A dict containing 'json' key with booking data.

    Returns:
        A tuple of (status_code, body_dict) representing the HTTP response.
    """
    try:
        # Extract and validate required fields
        if not isinstance(request, dict):
            raise ValueError("Request must be a dictionary")

        data = request.get('json', {})
        if not isinstance(data, dict):
            raise ValueError("Request 'json' field must be a dictionary")

        room_id = data.get('room_id')
        start_str = data.get('start')
        end_str = data.get('end')

        # Validate required fields exist and are correct types
        if not all([room_id, start_str, end_str]):
            missing_fields = []
            if not room_id:
                missing_fields.append("room_id")
            if not start_str:
                missing_fields.append("start")
            if not end_str:
                missing_fields.append("end")

            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            return (400, {"error": error_msg})

        # Validate types
        if not isinstance(room_id, str):
            return (400, {"error": "room_id must be a string"})

        if not isinstance(start_str, str) or not isinstance(end_str, str):
            return (400, {"error": "start and end must be ISO 8601 datetime strings"})

        # Validate room_id is in KNOWN_ROOMS
        if room_id not in KNOWN_ROOMS:
            return (404, {"error": f"Room '{room_id}' not found in known rooms"})

        # Parse and validate ISO 8601 datetime strings
        try:
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
        except ValueError as e:
            return (400, {"error": f"Invalid ISO 8601 format: {e}"})

        # Validate end is after start
        if end <= start:
            return (400, {"error": "end datetime must be after start datetime"})

        # Calculate duration in hours
        duration = (end - start).total_seconds() / 3600
        max_duration_hours = 4.0

        if duration > max_duration_hours:
            return (422, {"error": f"Booking duration ({duration:.1f}h) exceeds maximum allowed duration of {max_duration_hours} hours"})

        # Success case
        return (201, {
            "room_id": room_id,
            "start": start_str,
            "end": end_str
        })

    except Exception as e:
        return (400, {"error": f"Internal server error: {str(e)}"})
```