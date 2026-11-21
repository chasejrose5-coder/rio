import assert from "node:assert/strict";
import test from "node:test";
import { FOAM_AREAS, FOAM_DISCLAIMER, foamRoutine } from "./foam-content.ts";

const quality = { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] };
const longRun = {
  date: "2026-11-14",
  day_of_week: "Saturday",
  template_id: "aer_12000_r0_x1",
  reason_codes: ["weekly_aerobic_long_run"],
};
const race = { date: "2026-11-14", day_of_week: "Saturday", template_id: "rr_800_r0_x1", reason_codes: [] as string[] };

test("every area has a one-line how-to", () => {
  assert.equal(FOAM_DISCLAIMER.includes("Not medical advice"), true);
  assert.equal(FOAM_AREAS.length, 7);
  for (const area of FOAM_AREAS) {
    assert.ok(area.howTo.length > 20);
    assert.equal(area.howTo.includes("\n"), false);
  }
});

test("a hard day and a long run are a minute per area, and other days are optional", () => {
  const hard = foamRoutine("2026-11-10", [quality]);
  assert.equal(hard.required, true);
  assert.equal(hard.seconds, 7 * 60);
  assert.equal(hard.areas.length, 7);
  assert.ok(hard.areas.every((area) => area.seconds === 60));
  assert.match(hard.label, /After this workout/);

  const long = foamRoutine("2026-11-14", [longRun]);
  assert.equal(long.required, true);
  assert.equal(long.areas[0]?.seconds, 60);

  const easy = foamRoutine("2026-11-11", [quality]);
  assert.equal(easy.required, false);
  assert.equal(easy.seconds, 7 * 30);
  assert.match(easy.label, /Optional/);

  const raced = foamRoutine("2026-11-14", [race]);
  assert.equal(raced.required, false);
  const eve = foamRoutine("2026-11-13", [race]);
  assert.equal(eve.required, false);
});

test("the order rotates across the week and the next week", () => {
  const tuesday = foamRoutine("2026-11-10", [quality]).areas.map((area) => area.id);
  const wednesday = foamRoutine("2026-11-11", [quality]).areas.map((area) => area.id);
  assert.notEqual(tuesday[0], wednesday[0]);
  assert.deepEqual(new Set(tuesday).size, 7);
  const next = foamRoutine("2026-11-17", [
    { date: "2026-11-17", day_of_week: "Tuesday", template_id: "se_400_r90_x6", reason_codes: ["phase_4"] },
  ]).areas.map((area) => area.id);
  assert.notDeepEqual(tuesday, next);
});
