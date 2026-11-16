import assert from "node:assert/strict";
import test from "node:test";
import { PRIVATE_PREFIXES, PUBLIC_PATHS } from "./public-routes.ts";

test("the sitemap list is only the public pages", () => {
  assert.ok(PUBLIC_PATHS.includes("/"));
  assert.ok(PUBLIC_PATHS.includes("/about"));
  assert.ok(PUBLIC_PATHS.includes("/sign-in"));
  assert.ok(PUBLIC_PATHS.includes("/privacy"));
  assert.ok(PUBLIC_PATHS.includes("/terms"));
  for (const path of PUBLIC_PATHS) {
    assert.equal(PRIVATE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`)), false, path);
  }
  for (const blocked of ["/home", "/plan", "/library", "/api"]) {
    assert.equal(PUBLIC_PATHS.includes(blocked as (typeof PUBLIC_PATHS)[number]), false);
    assert.ok(PRIVATE_PREFIXES.includes(blocked as (typeof PRIVATE_PREFIXES)[number]));
  }
  assert.equal(PRIVATE_PREFIXES.includes("/about" as (typeof PRIVATE_PREFIXES)[number]), false);
});
