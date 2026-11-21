import assert from "node:assert/strict";
import test from "node:test";
import {
  AREAS,
  BONE_MESSAGE,
  EXERCISES,
  GENERAL_IDS,
  INJURY_DISCLAIMER,
  dayBlocks,
  exercisesFor,
  generalExerciseIds,
  generalOffsets,
  isGeneralDay,
  isRebuildingDay,
  levelOn,
} from "./injury-content.ts";

test("every exercise has three doses and a one-line how-to, and every area is real", () => {
  const areaIds = new Set(AREAS.map((area) => area.id));
  assert.equal(INJURY_DISCLAIMER.includes("Not medical advice"), true);
  assert.equal(BONE_MESSAGE.includes("See a doctor first"), true);
  for (const exercise of EXERCISES) {
    assert.ok(areaIds.has(exercise.areaId), exercise.id);
    assert.ok(exercise.howTo.length > 20, exercise.id);
    assert.equal(exercise.howTo.includes("\n"), false, exercise.id);
    for (const level of ["easy", "medium", "hard"] as const) {
      assert.ok(exercise.doses[level], `${exercise.id} ${level}`);
    }
  }
  for (const id of GENERAL_IDS) {
    assert.ok(EXERCISES.some((exercise) => exercise.id === id), id);
  }
  for (const area of AREAS) {
    const count = EXERCISES.filter((exercise) => exercise.areaId === area.id).length;
    if (area.bone) assert.equal(count, 0, area.id);
    else assert.ok(count >= 2, area.id);
  }
});

test("a level stays easy for 13 days, then steps up every 14 days", () => {
  assert.equal(levelOn(0, "2026-11-01", "2026-11-01"), "easy");
  assert.equal(levelOn(0, "2026-11-01", "2026-11-14"), "easy");
  assert.equal(levelOn(0, "2026-11-01", "2026-11-15"), "medium");
  assert.equal(levelOn(0, "2026-11-01", "2026-11-29"), "hard");
  assert.equal(levelOn(1, "2026-11-10", "2026-11-10"), "medium");
  assert.equal(levelOn(2, "2026-11-10", "2026-12-20"), "hard");
  assert.equal(levelOn(0, "2026-12-01", "2026-11-01"), "easy");
});

test("general prevention is two or three days, and a rebuilding area is three other days", () => {
  const monday = "2026-11-09";
  const offsets = generalOffsets(monday);
  assert.ok(offsets.length === 2 || offsets.length === 3);
  assert.equal(offsets.includes(1), true);
  let general = 0;
  let rebuilding = 0;
  for (let day = 8; day <= 14; day += 1) {
    const date = `2026-11-${String(day).padStart(2, "0")}`;
    if (isGeneralDay(date)) general += 1;
    if (isRebuildingDay(date)) rebuilding += 1;
  }
  assert.equal(general, offsets.length);
  assert.equal(rebuilding, 3);
  assert.equal(isGeneralDay("2026-11-08"), false);
  assert.equal(isRebuildingDay("2026-11-10"), true);
});

test("the general set rotates, and a race day and the day before stay clear", () => {
  const first = generalExerciseIds("2026-11-09");
  assert.equal(first.length, 4);
  const second = generalExerciseIds("2026-11-23");
  assert.equal(second.length, 4);
  assert.notDeepEqual(first, second);
  const race = { date: "2026-11-10", day_of_week: "Tuesday", template_id: "rr_800_r0_x1", reason_codes: [] };
  assert.equal(isGeneralDay("2026-11-09"), true);
  assert.ok(dayBlocks("2026-11-09", [], []).some((block) => block.id === "general"));
  assert.equal(dayBlocks("2026-11-09", [race], []).length, 0);
  assert.equal(dayBlocks("2026-11-10", [race], [{ areaId: "achilles", level: "easy" }]).length, 0);
});

test("a rebuilding area uses that level, bone stress does not load, and general work skips a duplicate", () => {
  const tuesday = dayBlocks("2026-11-10", [], [{ areaId: "achilles", level: "easy" }]);
  assert.equal(tuesday.some((block) => block.id === "general"), false);
  const achilles = tuesday.find((block) => block.id === "achilles");
  assert.ok(achilles);
  assert.deepEqual(
    achilles?.exercises.map((item) => item.exercise.name),
    ["Isometric calf-raise holds"],
  );
  assert.equal(achilles?.exercises[0]?.dose, "3×20 s");
  const hard = exercisesFor("achilles", "hard").map((item) => item.exercise.name);
  assert.deepEqual(hard, ["Weighted bent-knee calf raises", "Pogo hops"]);

  const bone = dayBlocks("2026-11-10", [], [{ areaId: "bone-stress", level: "easy" }]);
  assert.equal(bone[0]?.boneMessage, BONE_MESSAGE);
  assert.equal(bone[0]?.exercises.length, 0);

  const thursday = "2026-11-12";
  if (isGeneralDay(thursday) && isRebuildingDay(thursday)) {
    const both = dayBlocks(thursday, [], [{ areaId: "glute-med", level: "medium" }]);
    const general = both.find((block) => block.id === "general");
    const names = general?.exercises.map((item) => item.exercise.areaId) ?? [];
    assert.equal(names.includes("glute-med"), false);
  }
});
