import assert from "node:assert/strict";
import test from "node:test";
import { EXERCISES, REGIONS, ROUTINES, SHARP_MESSAGE } from "./stretch-content.ts";
import { poseIds, POSES } from "./stretch-poses.ts";
import {
  classifyDay,
  easyRoutineId,
  extraExercises,
  filterExercises,
  prescribe,
  spotState,
  weekLabel,
  weekProgress,
  type SoreSpot,
} from "./stretch-content.ts";

const BANNED = ["probability", "readiness_score", "Chase", "Jay Rose", "Jay"];

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function spot(partial: Partial<SoreSpot> & Pick<SoreSpot, "region" | "severity">): SoreSpot {
  return {
    started_on: "2026-11-10",
    check_in_on: "2026-11-17",
    cleared: false,
    ...partial,
  };
}

test("the library is the 42 named stretches, each with its own drawing", () => {
  assert.equal(EXERCISES.length, 42);
  assert.deepEqual(
    EXERCISES.map((exercise) => exercise.id),
    Array.from({ length: 42 }, (_, index) => index + 1),
  );
  assert.equal(new Set(EXERCISES.map((exercise) => exercise.name)).size, 42);
  assert.deepEqual(poseIds(), EXERCISES.map((exercise) => exercise.id));
  const drawings = poseIds().map((id) => JSON.stringify(POSES[id]));
  assert.equal(new Set(drawings).size, 42);
  for (const exercise of EXERCISES) {
    const count = sentences(exercise.howTo).length;
    assert.ok(count >= 2 && count <= 3, `${exercise.id} has ${count} sentences`);
    assert.ok(exercise.dose.length > 0);
    assert.ok(exercise.type === "D" || exercise.type === "S");
    for (const word of BANNED) assert.equal(exercise.howTo.includes(word), false, word);
  }
  assert.equal(EXERCISES[0].dose, "10 each way per foot");
  assert.equal(EXERCISES[41].name, "Neck side stretch");
  assert.equal(EXERCISES[41].type, "S");
});

test("routines keep the given order, ids, and times", () => {
  assert.deepEqual(
    ROUTINES.map((routine) => [routine.id, routine.minutes, [...routine.exerciseIds]]),
    [
      ["pre-run", 8, [1, 12, 26, 17, 21, 39]],
      ["post-run", 10, [5, 6, 14, 16, 19, 22]],
      ["long-recovery", 12, [3, 6, 20, 23, 28, 34, 31]],
      ["yoga", 12, [33, 8, 19, 23, 37, 38, 34]],
      ["hips", 10, [24, 25, 32, 22, 27, 29]],
      ["primer", 6, [1, 12, 26, 13, 21, 41]],
    ],
  );
});

test("each plan day type picks the matching routines", () => {
  const quality = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] },
  });
  assert.equal(quality.kind, "quality");
  assert.deepEqual(quality.routines.map((item) => item.routine.id), ["pre-run", "post-run"]);

  const thursday = classifyDay("2026-11-12", {
    date: "2026-11-12",
    day_of_week: "Thursday",
    template_id: "ap_600_r75_x6",
  });
  assert.equal(thursday, "quality");

  const easyTuesday = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "aer_5000_r0_x1", reason_codes: ["extra_easy_day"] },
  });
  assert.equal(easyTuesday.kind, "easy");
  assert.equal(easyRoutineId("2026-11-10"), "hips");
  assert.deepEqual(easyTuesday.routines.map((item) => item.routine.id), ["hips"]);

  const sunday = prescribe({
    today: "2026-11-15",
    session: { date: "2026-11-15", day_of_week: "Sunday", template_id: "aer_5000_r0_x1" },
  });
  assert.equal(sunday.kind, "easy");
  assert.deepEqual(sunday.routines.map((item) => item.routine.id), ["hips"]);

  const monday = prescribe({
    today: "2026-11-16",
    session: { date: "2026-11-16", day_of_week: "Monday", template_id: "aer_5000_r0_x1" },
  });
  assert.equal(monday.kind, "easy");
  assert.equal(easyRoutineId("2026-11-16"), "yoga");
  assert.deepEqual(monday.routines.map((item) => item.routine.id), ["yoga"]);

  const wednesdayHold = prescribe({
    today: "2026-11-11",
    session: {
      date: "2026-11-11",
      day_of_week: "Wednesday",
      template_id: "aer_10000_r0_x1",
      reason_codes: ["weekly_aerobic_long_run", "extra_easy_day"],
    },
  });
  assert.equal(wednesdayHold.kind, "easy");
  assert.deepEqual(wednesdayHold.routines.map((item) => item.routine.id), ["yoga"]);

  const long = prescribe({
    today: "2026-11-14",
    session: {
      date: "2026-11-14",
      day_of_week: "Saturday",
      template_id: "aer_12000_r0_x1",
      reason_codes: ["weekly_aerobic_long_run"],
    },
  });
  assert.equal(long.kind, "long");
  assert.deepEqual(long.routines.map((item) => item.routine.id), ["pre-run", "long-recovery"]);

  const race = prescribe({
    today: "2026-11-14",
    session: { date: "2026-11-14", day_of_week: "Saturday", template_id: "rr_800_r0_x1" },
  });
  assert.equal(race.kind, "race");
  assert.deepEqual(race.routines.map((item) => item.routine.id), ["primer"]);

  const rest = prescribe({ today: "2026-11-13", session: null });
  assert.equal(rest.kind, "rest");
  assert.deepEqual(rest.routines.map((item) => item.routine.id), ["yoga"]);

  const emptyTuesday = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "" },
  });
  assert.equal(emptyTuesday.kind, "rest");

  const wrongDay = prescribe({
    today: "2026-11-13",
    session: { date: "2026-11-14", day_of_week: "Saturday", template_id: "aer_12000_r0_x1" },
  });
  assert.equal(wrongDay.kind, "rest");
});

test("mild and moderate spots add extras for 7 days, then ask, and sharp adds nothing", () => {
  const calves = spot({ region: "calves", severity: "moderate" });
  const onStart = extraExercises([calves], "2026-11-10").map((exercise) => exercise.id);
  assert.deepEqual(onStart, [5, 6, 8]);
  assert.equal(spotState(calves, "2026-11-16"), "active");
  assert.deepEqual(extraExercises([calves], "2026-11-16").map((exercise) => exercise.id), [5, 6, 8]);
  assert.equal(spotState(calves, "2026-11-17"), "check-in");
  assert.deepEqual(extraExercises([calves], "2026-11-17"), []);

  const prescribed = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    spots: [calves, spot({ region: "hamstrings", severity: "mild" })],
  });
  assert.deepEqual(prescribed.extras.map((exercise) => exercise.id), [5, 6, 8, 14, 15, 13]);
  assert.deepEqual(prescribed.routines.map((item) => item.routine.id), ["pre-run", "post-run"]);
  assert.equal(prescribed.sharp.length, 0);

  const sharp = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    spots: [spot({ region: "calves", severity: "sharp" })],
  });
  assert.deepEqual(sharp.extras, []);
  assert.equal(sharp.sharp[0]?.label, "Calves / Achilles");
  assert.match(SHARP_MESSAGE, /Stop stretching that area/);

  const cleared = prescribe({
    today: "2026-11-10",
    session: null,
    spots: [spot({ region: "neck", severity: "mild", cleared: true })],
  });
  assert.deepEqual(cleared.extras, []);
  assert.deepEqual(cleared.checkIns, []);

  const neck = extraExercises([spot({ region: "neck", severity: "mild" })], "2026-11-10");
  assert.deepEqual(neck.map((exercise) => exercise.id), [42]);
  const abs = REGIONS.find((region) => region.id === "abs");
  assert.deepEqual(abs?.extraIds, [33, 35, 36]);
});

test("done marks count for this week and the streak stops at a gap", () => {
  const progress = weekProgress(
    [
      { date: "2026-11-09", routine_id: "yoga" },
      { date: "2026-11-10", routine_id: "pre-run" },
      { date: "2026-11-10", routine_id: "post-run" },
      { date: "2026-11-08", routine_id: "hips" },
    ],
    "2026-11-10",
  );
  assert.equal(progress.routines, 4);
  assert.equal(progress.days, 3);
  assert.equal(progress.streak, 3);
  assert.equal(weekLabel(progress), "4 routines done this week · 3-day streak");

  const gap = weekProgress([{ date: "2026-11-08", routine_id: "yoga" }], "2026-11-10");
  assert.equal(gap.streak, 0);
  assert.match(weekLabel(gap), /No streak yet/);

  const done = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    completions: [{ date: "2026-11-10", routine_id: "pre-run" }],
  });
  assert.equal(done.routines[0]?.done, true);
  assert.equal(done.routines[1]?.done, false);
});

test("the library filters by area and by dynamic or static", () => {
  assert.equal(filterExercises("All", "All").length, 42);
  assert.equal(filterExercises("Hamstrings", "All").length, 4);
  assert.deepEqual(
    filterExercises("Hamstrings", "S").map((exercise) => exercise.id),
    [14, 15],
  );
  assert.equal(filterExercises("Shins", "D").length, 2);
});
