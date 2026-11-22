import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { clearClientSession } from "./api.ts";
import { heartRateSatisfied, landingPath, markHeartRateSaved, resetHeartRateSaved, subscribeHeartRate } from "./landing.ts";
import type { CurrentSeason } from "./types.ts";

function season(goal: string, today: string): CurrentSeason {
  return {
    today,
    inputs: { current_time: "2:05.0", start_date: "2026-09-01", goal_time: "1:59.0", goal_date: goal },
  };
}

describe("landing", () => {
  it("forgets a saved heart rate when the session is cleared", () => {
    markHeartRateSaved({ resting_hr: 50, max_hr: 180 });
    assert.equal(heartRateSatisfied(), true);
    let heard = 0;
    const stop = subscribeHeartRate(() => {
      heard += 1;
    });
    clearClientSession();
    assert.equal(heartRateSatisfied(), false);
    assert.equal(heard, 1);
    resetHeartRateSaved();
    assert.equal(heard, 2);
    stop();
    assert.equal(heartRateSatisfied(), false);
  });

  it("sends a goal of today home, yesterday to start, and no season to start", () => {
    assert.equal(landingPath(null), "/start");
    assert.equal(landingPath(season("2026-11-10", "2026-11-10")), "/home");
    assert.equal(landingPath(season("2026-11-09", "2026-11-10")), "/start");
    assert.equal(landingPath(season("2026-11-11", "2026-11-10")), "/home");
  });
});