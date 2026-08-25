def fetch_active_records(user_id):
    # Archived records are excluded per the retention policy (ADR-019).
    records = fetch_records(user_id)
    active = [r for r in records if not r.archived]
    return active
