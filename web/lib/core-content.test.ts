import assert from "node:assert/strict";
import test from "node:test";
import { CATEGORIES, CORE_DISCLAIMER, CORE_EXERCISES, circuitFor, weekCircuits } from "./core-content.ts";

const race = { date: "2026-11-14", day_of_week: "Saturday", template_id: "rr_800_r0_x1", reason_codes: [] as string[] };
const quality = { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] };
const longRun = {
  date: "2026-11-14",
  day_of_week: "Saturday",
  template_id: "aer_12000_r0_x1",
  reason_codes: ["weekly_aerobic_long_run"],
};

test("the library has the five categories, a dose, and a one-line how-to", () => {
  assert.equal(CORE_DISCLAIMER.includes("Not medical advice"), true);
  const seen = new Set(CORE_EXERCISES.map((exercise) => exercise.category));
  assert.deepEqual([...seen], [...CATEGORIES]);
  for (const category of CATEGORIES) {
    assert.equal(CORE_EXERCISES.filter((exercise) => exercise.category === category).length, 4);
  }
  for (const exercise of CORE_EXERCISES) {
    assert.ok(exercise.dose);
    assert.ok(exercise.howTo.length > 20);
    assert.equal(exercise.howTo.includes("\n"), false);
    assert.equal(exercise.seconds, 80);
  }
});

test("a hard day is about 8 minutes, an easy day is 12 to 15, and a race day is empty", () => {
  const hard = circuitFor("2026-11-10", [quality]);
  assert.ok(hard);
  assert.ok(hard.seconds >= 7 * 60 && hard.seconds <= 9 * 60, String(hard.seconds));
  assert.equal(hard.label, "About 8 min");
  const names = new Set(hard.exercises.map((exercise) => exercise.category));
  assert.ok(names.size >= 4);

  const easy = circuitFor("2026-11-11", [quality]);
  assert.ok(easy);
  assert.ok(easy.seconds >= 12 * 60 && easy.seconds <= 15 * 60, String(easy.seconds));

  const long = circuitFor("2026-11-14", [longRun]);
  assert.ok(long);
  assert.ok(long.seconds >= 7 * 60 && long.seconds <= 9 * 60);

  assert.equal(circuitFor("2026-11-14", [race]), null);
  assert.equal(circuitFor("2026-11-13", [race]), null);
});

test("a week uses every category, and the next week changes the exercises", () => {
  const week = weekCircuits("2026-11-10", [quality]);
  const categories = new Set<string>();
  for (const circuit of week.values()) {
    if (!circuit) continue;
    for (const exercise of circuit.exercises) categories.add(exercise.category);
  }
  assert.equal(categories.size, CATEGORIES.length);
  const first = circuitFor("2026-11-10", [quality])?.exercises.map((exercise) => exercise.id);
  const later = circuitFor("2026-11-17", [
    { date: "2026-11-17", day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] },
  ])?.exercises.map((exercise) => exercise.id);
  assert.ok(first && later);
  assert.notDeepEqual(first, later);
});
