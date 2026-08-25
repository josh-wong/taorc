function normalize(text: string): string {
  return text.trim();
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================
function slugify(text: string): string {
  return text.toLowerCase().replace(/ /g, "-");
}
