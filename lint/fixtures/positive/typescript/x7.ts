function fetchActiveRecords(userId: string) {
  // Step 1: Get the user's records
  const records = fetchRecords(userId);
  return records.filter((r) => !r.archived);
}
