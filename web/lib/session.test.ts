import assert from "node:assert/strict";
import test from "node:test";
import { PREP, acceptTimeKey, confirmCopy, filledTimes, sessionHref, watchlessSummary } from "./session.ts";

test("start session uses the next planned day", () => {
  assert.equal(sessionHref("2026-11-10"), "/session?date=2026-11-10");
  assert.equal(sessionHref(""), "/session");
  assert.equal(sessionHref(null), "/session");
});

test("rep boxes ignore a keystroke that is not a time", () => {
  assert.equal(acceptTimeKey("71", "71a"), "71");
  assert.equal(acceptTimeKey("", "71.2"), "71.2");
  assert.equal(filledTimes(["71.2", "", "70"]), "71.2, 70");
});

test("confirm copy matches the dialog", () => {
  assert.equal(confirmCopy("result"), "Confirm this result before the plan changes.");
  assert.equal(confirmCopy("workout"), "Confirm this workout before the plan changes.");
});

test("prep notes are the four fixed blocks", () => {
  assert.deepEqual(
    PREP.map((block) => block.title),
    ["Pre-warm-up", "Warm-up", "Cool-down", "Core"],
  );
  assert.equal(PREP[0].lines[0], "1 × 800 m easy");
  assert.ok(PREP[1].groups[2].includes("4 × 100 m strides with walk-back"));
  assert.equal(PREP[3].groups[0].length, 8);
});

test("a finished no-watch row reads completed", () => {
  assert.equal(watchlessSummary({ mark: "on_track", text: "1:12.4" }), "Completed · On target · 1:12.4");
  assert.equal(watchlessSummary({}), "Completed");
});
