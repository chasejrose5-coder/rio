import assert from "node:assert/strict";
import test from "node:test";
import { canonicalEasyPace, cleanGoal, easyPacePhrase, savedPaceLine, shownField } from "./profile.ts";

test("a goal time matches Start, and blank or zero is not one", () => {
  for (const sample of ["1:55.0", "2:02.9", "1:55", "0:01", "12:00.50", "1:75", " 1:55.0 "]) {
    assert.equal(cleanGoal(sample), sample.trim());
  }
  for (const sample of ["", "155", "1:5", "0:00", "0:00.0", "1:55.0s", "1:55.0\nno"]) {
    assert.equal(cleanGoal(sample), null);
  }
});

test("easy pace is minutes and seconds, between one minute and thirty", () => {
  assert.equal(canonicalEasyPace("7:25"), "7:25");
  assert.equal(canonicalEasyPace("07:05"), "7:05");
  assert.equal(canonicalEasyPace("5:00.0"), "5:00");
  assert.equal(canonicalEasyPace("0:59"), null);
  assert.equal(canonicalEasyPace("30:01"), null);
  assert.equal(canonicalEasyPace("7:60"), null);
  assert.equal(canonicalEasyPace("fast"), null);
  assert.equal(easyPacePhrase("5:00", "km"), "5:00 per kilometer");
  assert.equal(easyPacePhrase("7:25", "mi"), "7:25 per mile");
  assert.equal(easyPacePhrase("nope", "km"), "");
  assert.equal(savedPaceLine("7:25 per mile"), "Saved: 7:25 per mile. You can change it here.");
  assert.equal(savedPaceLine(""), "");
});

test("a blank profile value is an em dash, and a short date is the stored day", () => {
  assert.equal(shownField("Current 800 time", "", "iso"), "—");
  assert.equal(shownField("Current 800 time", "—", "iso"), "—");
  assert.equal(shownField("Current 800 time", "2:02.9", "short"), "2:02.9");
  assert.equal(shownField("Start date", "2026-04-19", "iso"), "2026-04-19");
  assert.equal(shownField("Goal date", "2027-03-19", "short"), "Mar 19, 2027");
  assert.equal(shownField("Start date", "—", "short"), "—");
});
