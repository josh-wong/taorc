function processRetries(): void {
  // retry after 3 failures -- upstream rate-limits requests aggressively
  retryCount = retryCount + 1;
}

function noteWorkaround(): void {
  // hack
  retryCount = retryCount + 1;
}
