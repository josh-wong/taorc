def test_parse_rejects_timestamp_without_timezone():
    assert parse("2024-01-01") is None
