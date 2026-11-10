import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { navShouldArm, pageShouldRise } from "./motion.ts";

describe("nav underline", () => {
  it("grows when the page changes and stays put on the same page", () => {
    assert.equal(navShouldArm(null, "/home"), true);
    assert.equal(navShouldArm("/home", "/plan"), true);
    assert.equal(navShouldArm("/home", "/home"), false);
  });

  it("rises the first time a page is shown and not on the same page again", () => {
    assert.equal(pageShouldRise(null, "home"), true);
    assert.equal(pageShouldRise("plan", "home"), true);
    assert.equal(pageShouldRise("home", "home"), false);
  });
});
