def process_retries():
    # retry after 3 failures -- upstream rate-limits requests aggressively
    retry_count = retry_count + 1


def note_workaround():
    # hack
    retry_count = retry_count + 1
