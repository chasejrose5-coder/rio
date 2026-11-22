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

test("a time that is already m:ss.c stays, and letters stay for the server check", () => {
  assert.equal(commitRaceTime("2:05.0"), "2:05.0");
  assert.equal(commitRaceTime("1:58.0"), "1:58.0");
  assert.equal(maskRaceTime("nope"), "nope");
  assert.equal(commitRaceTime("nope"), "nope");
});

test("a 400 m rep uses seconds.hundredths", () => {
  assert.equal(maskRepTime("50"), "50");
  assert.equal(maskRepTime("5090"), "50.90");
  assert.notEqual(maskRepTime("5090"), "5090");
});
