import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("targets, focus, scroll hints, and font preloads stay in place", () => {
  const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
  const layout = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(css, /\.rio-brand[\s\S]*?min-width:\s*44px/);
  assert.match(css, /\.rio-brand[\s\S]*?min-height:\s*44px/);
  assert.match(css, /\.rio-legal-links a \{ min-width: 44px/);
  assert.match(css, /\.rio-auth-card input:focus-visible[\s\S]*?outline: 2px solid/);
  assert.equal(css.includes(".rio-auth-card input:focus { border-color: #c94a25; outline: none; }"), false);
  assert.match(css, /\.rio-subnav[\s\S]*?scroll-snap-type: x proximity/);
  assert.match(css, /\.rio-phase \{[\s\S]*?min-height:\s*max\(44px,\s*3\.25rem\)/);
  assert.match(css, /\.rio-phase-bar[\s\S]*?display:\s*flex/);
  assert.equal(/\.rio-phases[\s\S]*?scroll-snap-type/.test(css), false);
  assert.match(css, /max-width: 360px/);
  assert.match(css, /\.rio-meaning a \{[\s\S]*?min-height:\s*44px/);
  assert.match(css, /\.rio-overflow \{[\s\S]*?flex: 1 1 0/);
  const splash = readFileSync(new URL("../components/Splash.tsx", import.meta.url), "utf8");
  const auth = readFileSync(new URL("../components/AuthScreen.tsx", import.meta.url), "utf8");
  assert.match(splash, /<main className="rio-splash-copy">/);
  assert.match(auth, /<main className="auth-screen">/);
  assert.match(layout, /return r\.text\(\)/);
  assert.match(layout, /AbortSignal\.timeout/);
  for (const file of [
    "inter-latin-500-normal.woff2",
    "inter-latin-600-normal.woff2",
    "manrope-latin-800-normal.woff2",
  ]) {
    assert.match(layout, new RegExp(file));
  }
});
