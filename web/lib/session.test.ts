import assert from "node:assert/strict";
import test from "node:test";
import { prepFor, acceptTimeKey, confirmCopy, filledTimes, nextSessionDate, sessionHref, sessionKind, watchlessSummary } from "./session.ts";

test("start session uses the next planned day", () => {
  assert.equal(sessionHref("2026-11-10"), "/session?date=2026-11-10");
  assert.equal(sessionHref(""), "/session");
  assert.equal(sessionHref(null), "/session");
  assert.equal(
    nextSessionDate({
      today: "2026-11-11",
      plan: { sessions: [{ date: "2026-11-10" }, { date: "2026-11-12" }, { date: "nope" }] },
    }),
    "2026-11-12",
  );
  assert.equal(
    nextSessionDate({ today: "2026-12-01", plan: { sessions: [{ date: "2026-11-10" }] } }),
    "2026-11-10",
  );
  assert.equal(nextSessionDate(null), null);
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

test("easy days jog, swing, and stretch, and other days keep the drills", () => {
  const easy = prepFor({ template_id: "aer_8000_r0_x1", day_of_week: "Monday", reason_codes: ["extra_easy_day"] });
  assert.deepEqual(
    easy.map((block) => block.title),
    ["Warm-up", "Cool-down", "Core"],
  );
  assert.equal(easy[0].lines?.[0], "3–5 min easy jog");
  assert.equal(easy[0].lead?.[0], "Then leg swings and a few light stretches:");
  const easyText = JSON.stringify(easy);
  assert.equal(easyText.includes("A-skips"), false);
  assert.equal(easyText.includes("strides"), false);
  assert.equal(easyText.includes("Active drills"), false);
  assert.equal(sessionKind({ template_id: "aer_12000_r0_x1", day_of_week: "Saturday", reason_codes: ["weekly_aerobic_long_run"] }), "long");

  for (const session of [
    { template_id: "se_400_r90_x6", day_of_week: "Tuesday", reason_codes: ["phase_4"] },
    { template_id: "rr_800_r0_x1", day_of_week: "Saturday", reason_codes: [] },
    { template_id: "aer_12000_r0_x1", day_of_week: "Saturday", reason_codes: ["weekly_aerobic_long_run"] },
  ]) {
    const full = prepFor(session);
    assert.deepEqual(
      full.map((block) => block.title),
      ["Pre-warm-up", "Warm-up", "Cool-down", "Core"],
    );
    assert.equal(full[0].lines?.[0], "1 × 800 m easy");
    assert.ok(full[1].groups?.[2].includes("4 × 100 m strides with walk-back"));
    assert.equal(full[3].groups?.[0].length, 8);
    assert.equal(JSON.stringify(full).includes("3–5 min easy jog"), false);
  }
});

test("a finished no-watch row reads completed", () => {
  assert.equal(watchlessSummary({ mark: "on_track", text: "1:12.4" }), "Completed · On track · 1:12.4");
  assert.equal(watchlessSummary({}), "Completed");
});
