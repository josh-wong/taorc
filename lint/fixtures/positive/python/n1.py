def load_settings():
    data = fetch_raw_config()
    validated = validate_schema(data)
    apply_defaults(validated)
    return validated
