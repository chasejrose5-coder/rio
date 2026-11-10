import assert from "node:assert/strict";
import test from "node:test";
import { browserClearNote, nameNote, normalizeName, seasonFile, shownName, TIME_ZONES, zoneOptions } from "./settings.ts";

test("the time zone list runs from UTC through Auckland", () => {
  assert.equal(TIME_ZONES[0], "UTC");
  assert.equal(TIME_ZONES[TIME_ZONES.length - 1], "Pacific/Auckland");
  assert.equal(TIME_ZONES.includes("America/Los_Angeles"), true);
});

test("a saved zone outside the list still appears first", () => {
  assert.deepEqual(zoneOptions("America/Detroit").slice(0, 2), ["America/Detroit", "UTC"]);
  assert.equal(zoneOptions("Pacific/Auckland")[0], "UTC");
});

test("a name is a short string of letters", () => {
  assert.equal(normalizeName("  Ada   Lovelace "), "Ada Lovelace");
  assert.equal(normalizeName(""), null);
  assert.equal(normalizeName("!!!"), null);
  assert.equal(normalizeName("A".repeat(41)), null);
});

test("the nickname wins, and a blank nickname falls back", () => {
  assert.equal(shownName("Chase", "CJ"), "CJ");
  assert.equal(shownName("Chase", "   "), "Chase");
});

test("hosted and local notes stay the Streamlit sentences", () => {
  assert.equal(nameNote("hosted"), "First name is enough. Saved to your RIO account.");
  assert.equal(nameNote("local"), "First name is enough. Saved on this machine.");
  assert.equal(browserClearNote("hosted"), "Signs you out on this browser. Your season stays in your account.");
  assert.equal(browserClearNote("local"), "Clears this browser. The account stays on this machine.");
});

test("the export is JSON with the four inputs and no secrets", () => {
  const text = seasonFile({
    inputs: {
      current_time: "2:02.9",
      start_date: "2026-04-19",
      goal_time: "1:55.0",
      goal_date: "2027-03-19",
    },
    plan: { season_length_weeks: 12, probability: 0.2, sessions: [{ template_id: "aer_800_r0_x1", readiness: 1 }] },
    marks: { "1": "on_track" },
    actuals: {},
  });
  const parsed = JSON.parse(text) as Record<string, unknown>;
  assert.equal(parsed.current_time, "2:02.9");
  assert.equal(parsed.start_date, "2026-04-19");
  assert.equal(parsed.goal_time, "1:55.0");
  assert.equal(parsed.goal_date, "2027-03-19");
  assert.equal(text.includes("probability"), false);
  assert.equal(text.includes("readiness"), false);
  assert.equal(text.includes("password"), false);
  assert.equal(text.includes("seal"), false);
  assert.equal(text.indexOf('"actuals"') < text.indexOf('"current_time"'), true);
});
