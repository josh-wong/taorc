def normalize(text):
    return text.strip()


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def slugify(text):
    return text.lower().replace(" ", "-")
