import assert from "node:assert/strict";
import test from "node:test";
import { linkFromParams, monthsLater, planHasScore, sameSeason, startFormDefaults, startOn } from "./start-form.ts";

test("goal date is five calendar months later, and a short month keeps its last day", () => {
  assert.equal(monthsLater("2026-11-01", 5), "2027-04-01");
  assert.equal(monthsLater("2026-12-15", 5), "2027-05-15");
  assert.equal(monthsLater("2026-01-31", 5), "2026-06-30");
  assert.equal(monthsLater("2026-03-31", 5), "2026-08-31");
  assert.equal(monthsLater("2023-09-30", 5), "2024-02-29");
  assert.equal(monthsLater("2024-09-30", 5), "2025-02-28");
});

test("start defaults leave the times blank", () => {
  const found = startFormDefaults("2026-11-10", "today");
  assert.deepEqual(found, {
    currentTime: "",
    startDate: "2026-11-10",
    goalTime: "",
    goalDate: "2027-04-10",
  });
});

test("next Sunday moves forward, and Sunday stays Sunday", () => {
  assert.equal(startOn("2026-11-10", "sunday"), "2026-11-15");
  assert.equal(startOn("2026-11-15", "sunday"), "2026-11-15");
  const sunday = startFormDefaults("2026-11-10", "sunday");
  assert.equal(sunday.startDate, "2026-11-15");
  assert.equal(sunday.goalDate, "2027-04-10");
});

test("a link is a different season until the four strings match", () => {
  const link = { current_time: "2:10.0", start_date: "2026-01-04", goal_time: "1:59.0", goal_date: "2026-06-04" };
  assert.equal(sameSeason(null, link), false);
  assert.equal(sameSeason({ current_time: "2:05.0", start_date: "2026-11-10", goal_time: "1:58.0", goal_date: "2027-04-10" }, link), false);
  assert.equal(sameSeason(link, link), true);
  assert.equal(linkFromParams(new URLSearchParams("current_time=2:10.0")), null);
});

test("a plan with a score is rejected", () => {
  assert.equal(planHasScore({ plan: { sessions: [] } }), false);
  assert.equal(planHasScore({ plan: { probability: 0.2 } }), true);
  assert.equal(planHasScore({ plan: { sessions: [{ readiness_score: 1 }] } }), true);
});
