import assert from "node:assert/strict";
import test from "node:test";
import { formatDate } from "./plan.ts";
import { formatSeasonDate, isPastSeason, openLabel, planQuery, rowLabel, seasonRows, unreadableMessage } from "./past.ts";
import type { StoredSeason } from "./types.ts";

function row(start: string, goal: string, time = "1:55.0", current = "2:05.0"): StoredSeason {
  return {
    inputs: { current_time: current, start_date: start, goal_time: time, goal_date: goal },
    stats: [{ label: "Season", value: `${start} – ${goal}` }, { label: "Goal time", value: time }],
  };
}

test("today is current and yesterday is past", () => {
  assert.equal(isPastSeason("2026-11-10", "2026-11-10"), false);
  assert.equal(isPastSeason("2026-11-09", "2026-11-10"), true);
});

test("rows keep the current season and sort by start date", () => {
  const rows = seasonRows(
    [row("2020-06-01", "2020-09-01"), row("2020-01-06", "2020-04-06")],
    [row("2026-04-19", "2027-03-19", "1:55.0", "2:02.9")],
  );
  assert.deepEqual(
    rows.map((item) => item.inputs.start_date),
    ["2020-01-06", "2020-06-01", "2026-04-19"],
  );
  assert.equal(rows.length, 3);
});

test("the same four inputs stay one row", () => {
  const one = row("2020-01-06", "2020-04-06");
  assert.equal(seasonRows([one], [one]).length, 1);
});

test("short dates are the link text and the plan query keeps the four inputs", () => {
  const inputs = row("2020-01-06", "2020-04-06").inputs;
  assert.equal(formatSeasonDate("2020-01-06", "short"), formatDate("2020-01-06", "short"));
  assert.equal(formatSeasonDate("2020-01-06", "iso"), formatDate("2020-01-06", "iso"));
  assert.equal(rowLabel(inputs, "short"), "Jan 6, 2020 Apr 6, 2020 1:55.0");
  assert.equal(rowLabel(inputs, "iso"), "2020-01-06 2020-04-06 1:55.0");
  assert.equal(openLabel(inputs), "2020-01-06 2020-04-06 1:55.0");
  const query = planQuery(inputs);
  assert.match(query, /current_time=2%3A05.0/);
  assert.match(query, /start_date=2020-01-06/);
  assert.match(query, /goal_date=2020-04-06/);
  assert.doesNotMatch(query, /\/seasons/);
});

test("an unreadable account uses the past-seasons sentence", () => {
  assert.equal(unreadableMessage("Accounts could not be read."), "This account's seasons could not be read.");
  assert.equal(unreadableMessage("Sign in again."), null);
});
