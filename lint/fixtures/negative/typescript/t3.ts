function testParseRejectsTimestampWithoutTimezone() {
  expect(parse("2024-01-01")).toBeNull();
}
