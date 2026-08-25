function fetchActiveRecords(userId: string) {
  // Archived records are excluded per the retention policy (ADR-019).
  const records = fetchRecords(userId);
  return records.filter((r) => !r.archived);
}
