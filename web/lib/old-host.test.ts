import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { LIVE_LABEL, LIVE_ORIGIN, isLegacyHost, isPreviewHost, requestHostname, showOldHomeNote } from "./old-host.ts";

test("the live site and a laptop do not count as old hosts", () => {
  for (const host of [
    "www.riorunning.com",
    "WWW.RIORunning.com",
    "www.riorunning.com.",
    "www.riorunning.com:443",
    "riorunning.com",
    "localhost",
    "localhost:3000",
    "127.0.0.1",
    "127.0.0.1:3000",
    "::1",
    "[::1]:3000",
    "",
    "   ",
    null,
    undefined,
  ]) {
    assert.equal(isLegacyHost(host), false, String(host));
  }
});

test("the old public hosts get the note", () => {
  for (const host of [
    "rio-one-mocha.vercel.app",
    "rio-rio-44fa.vercel.app",
    "riotraining.streamlit.app",
    "RIO-ONE-MOCHA.vercel.app",
    "rio-one-mocha.vercel.app:443",
  ]) {
    assert.equal(isLegacyHost(host), true, host);
  }
});

test("the public host wins over an internal host header", () => {
  assert.equal(
    requestHostname("www.riorunning.com", "rio-one-mocha.vercel.app"),
    "www.riorunning.com",
  );
  assert.equal(isLegacyHost(requestHostname("www.riorunning.com", "rio-one-mocha.vercel.app")), false);
  assert.equal(
    requestHostname("rio-one-mocha.vercel.app, internal", "www.riorunning.com"),
    "rio-one-mocha.vercel.app",
  );
  assert.equal(isLegacyHost(requestHostname(null, "rio-rio-44fa.vercel.app")), true);
  assert.equal(isLegacyHost(requestHostname("https://www.riorunning.com", "localhost:3000")), false);
  assert.equal(requestHostname("", "localhost:3000"), "localhost");
});

test("a preview deploy hides the note, and a production vercel host keeps it", () => {
  assert.equal(isPreviewHost("rio-git-cursor-uiux-enhancement-v4-c72e-rio-44fa.vercel.app"), true);
  assert.equal(isPreviewHost("rio-rio-44fa.vercel.app"), false);
  assert.equal(showOldHomeNote("rio-rio-44fa.vercel.app", "production"), true);
  assert.equal(showOldHomeNote("rio-one-mocha.vercel.app", ""), true);
  assert.equal(showOldHomeNote("rio-rio-44fa.vercel.app", "preview"), false);
  assert.equal(showOldHomeNote("rio-git-cursor-uiux-enhancement-v4-c72e-rio-44fa.vercel.app", "production"), false);
  assert.equal(showOldHomeNote("www.riorunning.com", "production"), false);
  assert.equal(showOldHomeNote("localhost", "preview"), false);
});

test("the note is a link on an old host and is not a redirect", () => {
  const note = readFileSync(new URL("../components/OldHomeNote.tsx", import.meta.url), "utf8");
  const layout = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(note, /RIO now lives at/);
  assert.match(note, /href=\{LIVE_ORIGIN\}/);
  assert.match(note, />\{LIVE_LABEL\}</);
  assert.equal(note.includes("redirect("), false);
  assert.equal(note.includes("window.location"), false);
  assert.match(layout, /<OldHomeNote \/>/);
  assert.match(layout, /<Suspense fallback=\{null\}>/);
  assert.equal(LIVE_ORIGIN, "https://www.riorunning.com");
  assert.equal(LIVE_LABEL, "riorunning.com");
});
