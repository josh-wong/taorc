def fetch_active_records(user_id):
    # Step 1: Get the user's records
    records = fetch_records(user_id)
    active = [r for r in records if not r.archived]
    return active
