import assert from "node:assert/strict";
import test from "node:test";
import {
  METHOD_SENTENCE,
  SAFETY_NOTE,
  anchorError,
  boundsError,
  formatRange,
  karvonenZones,
  maxHrFromAge,
  moveEdge,
  zonesMatch,
} from "./heart-rate.ts";

function edges(resting: number, max: number): Array<[number, number]> {
  return karvonenZones(resting, max).map((zone) => [zone.lowBpm, zone.highBpm]);
}

test("Karvonen zones match the heart-rate reserve percents", () => {
  assert.equal(maxHrFromAge(30), null);
  assert.equal(METHOD_SENTENCE, "Zones use the Karvonen (heart rate reserve) method.");
  assert.match(SAFETY_NOTE, /not medical advice/);
  assert.deepEqual(edges(60, 180), [
    [120, 132],
    [132, 144],
    [144, 156],
    [156, 168],
    [168, 180],
  ]);
  assert.deepEqual(edges(50, 200), [
    [125, 140],
    [140, 155],
    [155, 170],
    [170, 185],
    [185, 200],
  ]);
  assert.deepEqual(edges(62.5, 190), [
    [126, 139],
    [139, 152],
    [152, 165],
    [165, 177],
    [177, 190],
  ]);
  assert.deepEqual(
    karvonenZones(60, 180).map((zone) => zone.name),
    ["Recovery", "Easy / long", "Tempo", "Threshold", "VO2max / race"],
  );
  assert.equal(formatRange(120, 132), "120\u2013132");
  assert.equal(anchorError(60, 180), "");
  assert.equal(anchorError(100, 140), "");
  assert.match(anchorError(20, 180), /30 and 100/);
  assert.match(anchorError(60, 120), /140 and 230/);
  assert.match(anchorError(null, null), /30 and 100/);
});

test("a moved boundary stays shared with the next zone", () => {
  const defaults = karvonenZones(60, 180);
  const moved = moveEdge(defaults, 0, "high", 130);
  assert.equal(moved[0].highBpm, 130);
  assert.equal(moved[1].lowBpm, 130);
  assert.equal(boundsError(moved), "");
  assert.equal(zonesMatch(moved, defaults), false);
  const broken = moveEdge(defaults, 0, "low", 200);
  assert.match(boundsError(broken), /in order|30 and 230/);
});
