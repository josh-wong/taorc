def load_settings():
    data = fetch_raw_config()  # taorc-ignore: N1 -- legacy name, can't rename yet
    validated = validate_schema(data)
    apply_defaults(validated)
    return validated
