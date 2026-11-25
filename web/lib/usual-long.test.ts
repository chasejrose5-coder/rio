import assert from "node:assert/strict";
import test from "node:test";
import {
  LONG_MIN_M,
  formatUsualLong,
  longRunStartMeters,
  parseUsualLong,
  usualLongNote,
} from "./usual-long.ts";

test("miles and kilometers become meters, and the range is the one on the field", () => {
  assert.equal(parseUsualLong("", "miles"), null);
  assert.equal(parseUsualLong("8", "miles"), Math.round(8 * 1609.344));
  assert.equal(parseUsualLong("8.5", "miles"), Math.round(8.5 * 1609.344));
  assert.equal(parseUsualLong("13", "km"), 13000);
  assert.equal(parseUsualLong("13.2", "km"), 13200);
  assert.equal(parseUsualLong("2", "miles"), Math.round(2 * 1609.344));
  assert.equal(parseUsualLong("26", "miles"), Math.round(26 * 1609.344));
  assert.equal(parseUsualLong("3", "km"), 3000);
  assert.equal(parseUsualLong("42", "km"), 42000);
  assert.deepEqual(parseUsualLong("1.9", "miles"), { error: "Enter a distance between 2 and 26 mi." });
  assert.deepEqual(parseUsualLong("2.9", "km"), { error: "Enter a distance between 3 and 42 km." });
  assert.deepEqual(parseUsualLong("8.55", "miles"), { error: "Enter a distance between 2 and 26 mi." });
  assert.equal(formatUsualLong(Math.round(8 * 1609.344), "miles"), "8");
  assert.equal(formatUsualLong(Math.round(8.5 * 1609.344), "miles"), "8.5");
  assert.equal(formatUsualLong(13200, "km"), "13.2");
});

test("the first Saturday follows the 6 mile rule and stays on the 9.5 to 20 km ladder", () => {
  const six = Math.round(6 * 1609.344);
  assert.equal(six, 9656);
  assert.equal(longRunStartMeters(six), LONG_MIN_M);
  assert.match(usualLongNote(six), /9\.5 km/);
  const eight = Math.round(8 * 1609.344);
  assert.equal(longRunStartMeters(eight), 11000);
  assert.equal(usualLongNote(eight), "");
  assert.equal(longRunStartMeters(12000), 10000);
  assert.equal(longRunStartMeters(15000), 13000);
  assert.equal(longRunStartMeters(20000), 18000);
  assert.equal(longRunStartMeters(25000), 20000);
  assert.match(usualLongNote(25000), /20 km/);
  assert.equal(longRunStartMeters(8000), LONG_MIN_M);
});
