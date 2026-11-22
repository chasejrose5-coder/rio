import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { api, GET_CACHE_MS, prefetchHome } from "./api.ts";
import { heartPromptOpen, needsEasyPace, needsHeartRate, needsIntro, pathAfterSeason } from "./landing.ts";
import type { Athlete, CurrentSeason } from "./types.ts";

const athlete: Athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "hosted",
  today: "2026-11-11",
  prefs: { easy_pace: "7:45", intro_seen: true },
};

const season: CurrentSeason = {
  today: "2026-11-11",
  inputs: {
    current_time: "2:02.0",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
};

async function withFetch(fetchImpl: typeof fetch, run: () => Promise<void>): Promise<void> {
  const previous = globalThis.fetch;
  globalThis.fetch = fetchImpl;
  try {
    await run();
  } finally {
    globalThis.fetch = previous;
  }
}

describe("where sign-in lands", () => {
  it("asks for an easy pace, the intro, or Home without going through /", () => {
    assert.equal(needsEasyPace({ ...athlete, prefs: { easy_pace: "  " } }), true);
    assert.equal(pathAfterSeason({ ...athlete, prefs: { easy_pace: "" } }, season), "/easy-pace");
    assert.equal(pathAfterSeason({ ...athlete, prefs: { ...athlete.prefs, intro_seen: false } }, season), "/intro");
    assert.equal(pathAfterSeason({ ...athlete, prefs: { easy_pace: "7:45", intro_seen: null } }, null), "/intro");
    assert.equal(pathAfterSeason(athlete, null), "/start");
    assert.equal(pathAfterSeason({ ...athlete, prefs: { easy_pace: "7:45", intro_seen: null } }, season), "/home");
    assert.equal(needsIntro(athlete, season), false);
    assert.equal(needsHeartRate(null), false);
    assert.equal(needsHeartRate({ no_monitor: true, resting_hr: null, max_hr: null }), false);
    assert.equal(needsHeartRate({ no_monitor: false, resting_hr: null, max_hr: null }), true);
    assert.equal(needsHeartRate({ no_monitor: false, resting_hr: 60, max_hr: 180 }), false);
    assert.equal(pathAfterSeason(athlete, season), "/home");
    assert.equal(heartPromptOpen({ no_monitor: false, resting_hr: null, max_hr: null }, false), true);
    assert.equal(heartPromptOpen({ no_monitor: false, resting_hr: null, max_hr: null }, true), false);
    assert.equal(heartPromptOpen({ no_monitor: false, resting_hr: 60, max_hr: 180 }, false), false);
    assert.equal(heartPromptOpen({ no_monitor: false, resting_hr: null, max_hr: null }, false, true), false);
    assert.equal(heartPromptOpen(null, false), false);
    assert.equal(pathAfterSeason({ ...athlete, prefs: { easy_pace: "" } }, season), "/easy-pace");
    const routing = readFileSync(new URL("./enter.ts", import.meta.url), "utf8");
    assert.equal(routing.includes('return "/heart-rate"'), false);
    assert.equal(routing.includes("needsHeartRate"), false);
    assert.match(routing, /const seasonPromise = api\.currentSeason\(\)/);
    const seasonStart = routing.indexOf("const seasonPromise");
    const easyReturn = routing.indexOf('return "/easy-pace"');
    assert.ok(seasonStart !== -1 && easyReturn !== -1 && seasonStart < easyReturn);
    const enter = readFileSync(new URL("./enter.ts", import.meta.url), "utf8");
    const screen = readFileSync(new URL("../components/AuthScreen.tsx", import.meta.url), "utf8");
    assert.match(screen, /warmDestinationReads\(\)/);
    assert.match(screen, /<main className="auth-screen">/);
    const signIn = screen.slice(screen.indexOf("async function onSubmit"), screen.indexOf("export function CreateAccountScreen"));
    const warmed = signIn.indexOf("warmDestinationReads()");
    const refreshed = signIn.indexOf("const signedIn = await refresh()");
    assert.ok(warmed !== -1 && refreshed !== -1 && warmed < refreshed);
    const callback = readFileSync(new URL("../components/GoogleCallback.tsx", import.meta.url), "utf8");
    const button = readFileSync(new URL("../components/GoogleIdentityButton.tsx", import.meta.url), "utf8");
    assert.match(callback, /warmDestinationReads\(\)/);
    assert.match(button, /warmDestinationReads\(\)/);
    assert.ok(callback.indexOf("warmDestinationReads()") < callback.indexOf("const signedIn = await refresh()"));
    assert.ok(button.indexOf("warmDestinationReads()") < button.indexOf("const signedIn = await refresh()"));
    const gate = readFileSync(new URL("../components/Gate.tsx", import.meta.url), "utf8");
    assert.match(enter, /prefetchHome\(\)/);
    assert.match(enter, /markIntroLater\(\)/);
    assert.match(enter, /if \(destinationInflight\) return destinationInflight/);
    assert.equal(enter.includes('router.replace("/")'), false);
    assert.match(screen, /destinationAfterSignIn\(signedIn!\)/);
    assert.match(screen, /handoff\.current = true/);
    assert.match(screen, /if \(handoff\.current \|\| status !== "in"/);
    assert.match(gate, /destinationAfterSignIn\(athlete\)/);
    const home = readFileSync(new URL("../components/HomeView.tsx", import.meta.url), "utf8");
    assert.match(callback, /destinationAfterSignIn\(signedIn!\)/);
    assert.match(button, /destinationAfterSignIn\(signedIn!\)/);
    assert.equal(callback.includes('"/heart-rate"'), false);
    assert.equal(button.includes('"/heart-rate"'), false);
    assert.match(home, /HeartRatePrompt/);
    assert.match(home, /href="\/heart-rate"/);
    assert.match(gate, /status === "loading" \|\| status === "in"/);
    const loadingBranch = gate.indexOf('status === "loading" || status === "in"');
    const splash = gate.indexOf("<Splash");
    assert.ok(loadingBranch !== -1 && splash !== -1 && loadingBranch < splash);
    assert.equal(GET_CACHE_MS >= 30_000, true);
  });

  it("opens Home when the season read fails after sign-in", async () => {
    await withFetch(async (url) => {
      const path = String(url);
      if (path.includes("/seasons/current")) {
        return new Response(JSON.stringify({ detail: "down" }), { status: 500 });
      }
      return new Response(JSON.stringify({ detail: "no" }), { status: 404 });
    }, async () => {
      const { destinationAfterSignIn } = await import("./enter.ts");
      const path = await destinationAfterSignIn(athlete);
      assert.equal(path, "/home");
    });
  });

  it("reuses the Home prefetch until a write drops it", async () => {
    let homeCalls = 0;
    await withFetch(async (url, init) => {
      const path = String(url);
      const method = (init?.method || "GET").toUpperCase();
      if (method !== "GET") return new Response(JSON.stringify({ ok: true }), { status: 200 });
      if (path.includes("/home?")) {
        homeCalls += 1;
        return new Response(JSON.stringify({ hello: "cached" }), { status: 200 });
      }
      return new Response(JSON.stringify({ detail: "no" }), { status: 404 });
    }, async () => {
      await api.signOut();
      homeCalls = 0;
      const pending = prefetchHome();
      const home = await api.home(false);
      assert.equal(home.hello, "cached");
      await pending;
      assert.equal(homeCalls, 1);
      await api.home(false);
      assert.equal(homeCalls, 1);
      await api.patchSettings({ intro_seen: true });
      await api.home(false);
      assert.equal(homeCalls, 2);
    });
  });
});
