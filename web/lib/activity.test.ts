import assert from "node:assert/strict";
import test from "node:test";
import { formatSynced, heartChart, summaryTiles, volumeChart, zoneName } from "./activity.ts";

test("a sync time uses the settings zone, not UTC", () => {
  const when = Date.UTC(2026, 10, 10, 7, 30) / 1000;
  assert.equal(formatSynced(when, "America/Los_Angeles"), "Nov 9, 11:30 PM");
  assert.equal(formatSynced(when, "UTC"), "Nov 10, 7:30 AM");
  assert.equal(zoneName("", "America/Los_Angeles"), "America/Los_Angeles");
  assert.equal(zoneName("not-a-zone", ""), "UTC");
});

test("the heart chart drops a run with no heart rate and hides when none remain", () => {
  assert.equal(heartChart([{ date: "2026-11-09", bpm: 0 }, { date: "bad", bpm: 140 }]), null);
  const chart = heartChart([
    { date: "2026-11-09", bpm: 140 },
    { date: "2026-11-10", bpm: 0 },
  ]);
  assert.ok(chart);
  assert.equal(chart.dots.length, 1);
  assert.equal(chart.dots[0].date, "2026-11-09");
  assert.equal(chart.dots[0].label, "Nov 9");
});

test("this week tiles keep the six labels and an em dash for a missing distance", () => {
  const tiles = summaryTiles({ runs: 2, counts: { "On track": 1, Extra: 1 } });
  assert.deepEqual(
    tiles.map((tile) => tile.label),
    ["Distance", "Runs", "On track", "Ahead", "Behind", "Extra"],
  );
  assert.equal(tiles[0].value, "—");
  assert.equal(tiles[2].value, "1");
  assert.equal(tiles[5].value, "1");
});

test("the volume chart names miles and has no line when there are no weeks", () => {
  assert.equal(volumeChart([], "miles", [], 0), null);
  const chart = volumeChart([1609], "miles", ["1.0 mi"], 0);
  assert.ok(chart);
  assert.equal(chart.unit, "mi");
  assert.equal(chart.alone !== null, true);
});
