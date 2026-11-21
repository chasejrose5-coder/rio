import assert from "node:assert/strict";
import test from "node:test";
import {
  daysLabel,
  displayDistance,
  distancesFromRows,
  activityNotice,
  extrasBetween,
  formatDate,
  lengthText,
  linkError,
  phaseChipLabel,
  monthTitle,
  paceStatusLine,
  plainReason,
  goalLine,
  bikeLine,
  recapView,
  zoneRows,
  statusLabel,
  volumeLabel,
  weekContaining,
  weekOption,
  weekSpan,
  weekSunday,
} from "./plan.ts";

test("a phase chip reads as a week and a phase", () => {
  assert.equal(phaseChipLabel(12, "4"), "Week 12 · Phase 4");
  assert.equal(phaseChipLabel(1, "1"), "Week 1 · Phase 1");
});

test("season length says weeks, and one week stays singular", () => {
  assert.equal(lengthText(12), "12 weeks");
  assert.equal(lengthText(1), "1 week");
  assert.equal(lengthText(0), "—");
  assert.equal(lengthText(1.5), "—");
});

test("dates follow ISO or Short, and the month name is English", () => {
  assert.equal(formatDate("2026-10-24", "iso"), "2026-10-24");
  assert.equal(formatDate("2026-10-24", "short"), "Oct 24, 2026");
  assert.equal(formatDate("not-a-date", "iso"), "not-a-date");
  assert.equal(monthTitle("2026-10-01"), "October 2026");
});

test("a plan week opens on Sunday and contains today", () => {
  assert.equal(weekSunday("2026-11-10", 1), "2026-11-08");
  assert.equal(weekSunday("2026-11-08", 2), "2026-11-15");
  assert.equal(weekContaining("2026-11-10", 12, "2026-11-10"), 1);
  assert.equal(weekContaining("2026-11-10", 12, "2026-11-16"), 2);
  assert.equal(weekOption("2026-11-10", 1, "iso"), "Week 1 · 2026-11-08 — 2026-11-14");
  assert.equal(weekSpan("2026-11-10", 1, "4", "short"), "Phase 4 · Nov 8, 2026 — Nov 14, 2026");
  assert.equal(weekSpan("2026-11-10", 1, "—", "iso"), "2026-11-08 — 2026-11-14");
});

test("zero meters say no runs logged, and a logged week does not use a template", () => {
  assert.equal(volumeLabel(0, "0 m", "miles"), "No runs logged");
  assert.equal(volumeLabel(1200, "1,200 m", "km"), "1.2 km");
  assert.equal(daysLabel(1), "1 day to goal");
  assert.equal(daysLabel(12), "12 days to goal");
  assert.equal(daysLabel(null), "—");
  assert.equal(displayDistance("0 m", "miles"), "0.00 mi");
  assert.equal(displayDistance("0 m · 0 m the week before", "miles").includes("the week before"), true);
});

test("the goal line is the two times and the days left, with no score", () => {
  assert.equal(
    goalLine({ current: "2:05.0", goal: "1:58.0", goalDate: "2026-11-21", today: "2026-11-10" }),
    "2:05.0 now · 1:58.0 goal · 11 days left",
  );
  assert.equal(goalLine({ current: "2:05.0", goal: "1:58.0", goalDate: "2026-11-10", today: "2026-11-10" }).includes("today"), true);
  assert.equal(goalLine({ goalDate: "2026-11-09", today: "2026-11-10" }).includes("passed"), true);
  assert.equal(goalLine({ current: "2:05.0", goal: "1:58.0" }).includes("probability"), false);
  assert.equal(zoneRows(undefined), null);
  assert.equal(zoneRows([{ zone: 1, seconds: 0 }]), null);
  const shown = zoneRows([
    { zone: 2, name: "Easy / long", seconds: 60 },
    { zone: 5, name: "VO2max / race", seconds: 0 },
  ]);
  assert.equal(shown?.length, 2);
});

test("a week with no logged work does not invent meters", () => {
  const sessions = [
    { date: "2026-11-10", week_number: 1, day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] },
    { date: "2026-11-17", week_number: 2, day_of_week: "Tuesday", template_id: "aer_8000_r0_x1", reason_codes: ["extra_easy_week"] },
  ];
  const blank = recapView({ week: 1, sessions, actuals: {}, marks: {}, distances: {} });
  assert.equal(blank.completed, "0 of 1");
  assert.equal(blank.marks, "—");
  assert.equal(blank.volume, "0 m");
  assert.equal(blank.volume.includes("8,000"), false);
  const next = recapView({ week: 1, sessions, actuals: {}, marks: { "1": "on_track" }, distances: {} });
  assert.equal(next.completed, "Marked");
  assert.equal(next.marks, "On track");
  assert.equal(next.next, "Next week is an easy week.");
  const later = recapView({ week: 2, sessions, actuals: {}, marks: {}, distances: { "2026-11-10": 400 } });
  assert.equal(later.volume, "0 m · 400 m the week before");
  const ridden = recapView({
    week: 1,
    sessions,
    actuals: {},
    marks: {},
    distances: {},
    bikeDates: ["2026-11-10"],
  });
  assert.equal(ridden.completed, "1 of 1");
  assert.equal(ridden.volume, "0 m");
  const both = recapView({
    week: 1,
    sessions,
    actuals: { "2026-11-10": { template_id: "se_400_r90_x6", completed: true } },
    marks: {},
    distances: { "2026-11-10": 400 },
    bikeDates: ["2026-11-10"],
  });
  assert.equal(both.completed, "1 of 1");
  assert.equal(both.volume, "400 m");
  assert.equal(
    bikeLine({ minutes: 50, meters: 3218.688, zone2Seconds: 40, zoneSeconds: 50, units: "miles" }),
    "2.0 mi · 50 min · 80% in zone 2",
  );
  assert.equal(bikeLine({ minutes: 70, meters: 0, zone2Seconds: 0, zoneSeconds: 0, units: "km" }), "1h 10m");
  assert.equal(bikeLine({ minutes: 0, meters: 0, zone2Seconds: 0, zoneSeconds: 0, units: "miles" }), null);
  assert.equal(distancesFromRows([{ date: "2026-11-10", meters: 400 }, { date: "2026-11-11", meters: null }])["2026-11-10"], 400);
});

test("reasons are plain words, and an unknown code keeps its words", () => {
  assert.equal(plainReason("weekly_aerobic_long_run"), "The weekly long run");
  assert.equal(plainReason("phase_3"), "Phase 3");
  assert.equal(plainReason("custom_code"), "custom code");
  assert.equal(statusLabel(["phase_4", "weekly_aerobic_long_run"]), "Long");
  assert.equal(statusLabel(["phase_4"]), "");
  assert.equal(paceStatusLine("No runs yet"), "Pace status No runs yet.");
  assert.equal(paceStatusLine("On track"), "Pace status On track.");
});

test("extras are the unmatched runs inside Sunday through Saturday", () => {
  const rows = [
    { date: "2026-11-10", extra: true, name: "Shakeout" },
    { date: "2026-11-10", extra: false, name: "Planned" },
    { date: "2026-11-16", extra: true, name: "Outside" },
  ];
  const found = extrasBetween(rows, "2026-11-08", "2026-11-14");
  assert.deepEqual(found.map((row) => row.name), ["Shakeout"]);
});

test("the Strava card is only the missing-key notice", () => {
  assert.equal(activityNotice(null), null);
  assert.equal(activityNotice(""), null);
  assert.equal(activityNotice("Strava is not configured."), "missing");
  assert.equal(activityNotice("RIO_STRAVA_CLIENT_ID is not set."), "missing");
  assert.equal(activityNotice("the activity service returned 429"), "failed");
});

test("a bad shared link is the red sentence, and a normal plan URL is not", () => {
  assert.equal(linkError(new URLSearchParams()), "");
  assert.equal(
    linkError(new URLSearchParams("current_time=nope&start_date=2026-11-10&goal_time=1:58.0&goal_date=2027-04-10")),
    "current_time is not an 800 time",
  );
  assert.equal(
    linkError(new URLSearchParams("current_time=2:05.0&start_date=2026-11-10&goal_time=1:58.0&goal_date=2020-01-01")),
    "goal_date is before start_date",
  );
  assert.equal(
    linkError(new URLSearchParams("current_time=2:05.0&start_date=2026-11-10&goal_time=1:58.0&goal_date=2027-04-10")),
    "",
  );
});
