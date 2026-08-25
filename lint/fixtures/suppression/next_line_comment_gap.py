def load_settings():
    # taorc-ignore-next: N1 -- legacy name, can't rename yet
    # TODO: migrate this config loader off the legacy schema entirely
    data = fetch_raw_config()
    validated = validate_schema(data)
    apply_defaults(validated)
    return validated
