import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { navShouldArm } from "./motion.ts";

describe("nav underline", () => {
  it("grows when the page changes and stays put on the same page", () => {
    assert.equal(navShouldArm(null, "/home"), true);
    assert.equal(navShouldArm("/home", "/plan"), true);
    assert.equal(navShouldArm("/home", "/home"), false);
  });
});
