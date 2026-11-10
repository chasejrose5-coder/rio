import assert from "node:assert/strict";
import test from "node:test";
import { capacityClass, countLabel } from "./library.ts";

test("one workout stays singular", () => {
  assert.equal(countLabel(0), "0 workouts");
  assert.equal(countLabel(1), "1 workout");
  assert.equal(countLabel(82), "82 workouts");
});

test("a capacity pill keeps the family token, including underscores", () => {
  assert.equal(capacityClass("aerobic"), "rio-lib-cap rio-cap rio-cap-aerobic");
  assert.equal(capacityClass("speed_endurance"), "rio-lib-cap rio-cap rio-cap-speed_endurance");
  assert.equal(capacityClass("Aerobic Power!"), "rio-lib-cap rio-cap rio-cap-aerobicpower");
  assert.equal(capacityClass(""), "rio-lib-cap rio-cap");
});
