import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { landingPath } from "./landing.ts";
import type { CurrentSeason } from "./types.ts";

function season(goal: string, today: string): CurrentSeason {
  return {
    today,
    inputs: { current_time: "2:05.0", start_date: "2026-09-01", goal_time: "1:59.0", goal_date: goal },
  };
}

describe("landing", () => {
  it("sends a goal of today home, yesterday to start, and no season to start", () => {
    assert.equal(landingPath(null), "/start");
    assert.equal(landingPath(season("2026-11-10", "2026-11-10")), "/home");
    assert.equal(landingPath(season("2026-11-09", "2026-11-10")), "/start");
    assert.equal(landingPath(season("2026-11-11", "2026-11-10")), "/home");
  });
});