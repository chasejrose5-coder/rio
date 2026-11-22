import assert from "node:assert/strict";
import test from "node:test";
import { commitRaceTime, maskRaceTime, maskRepTime, raceTimeError } from "./time-mask.ts";

test("typing 202 becomes 2:02 and completes to 2:02.00", () => {
  assert.equal(maskRaceTime("2"), "2");
  assert.equal(maskRaceTime("20"), "2:0");
  assert.equal(maskRaceTime("202"), "2:02");
  assert.equal(maskRaceTime("202"), "2:02");
  assert.notEqual(maskRaceTime("202"), "202");
  assert.equal(commitRaceTime("202"), "2:02.00");
  assert.equal(raceTimeError("2:02.00"), "");
  assert.equal(raceTimeError("202"), "Enter a time like 2:02.00.");
});

test("a tenth pads to hundredths, and letters stay for the format check", () => {
  assert.equal(commitRaceTime("2:02.5"), "2:02.50");
  assert.equal(commitRaceTime("2:05.0"), "2:05.00");
  assert.equal(commitRaceTime("1:58.0"), "1:58.00");
  assert.equal(commitRaceTime("2020"), "2:02.00");
  assert.equal(raceTimeError(commitRaceTime("2:02.5")), "");
  assert.equal(raceTimeError("2:02.5"), "Enter a time like 2:02.00.");
  assert.equal(raceTimeError("2:60.00"), "Enter a time like 2:02.00.");
  assert.equal(maskRaceTime("nope"), "nope");
  assert.equal(commitRaceTime("nope"), "nope");
  assert.equal(raceTimeError("nope"), "Enter a time like 2:02.00.");
});

test("a 400 m rep uses seconds.hundredths", () => {
  assert.equal(maskRepTime("50"), "50");
  assert.equal(maskRepTime("5090"), "50.90");
  assert.notEqual(maskRepTime("5090"), "5090");
});
