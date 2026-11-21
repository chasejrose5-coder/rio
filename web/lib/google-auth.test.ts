import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { api, refreshSession } from "./api.ts";
import {
  GOOGLE_FAILED,
  clearGoogleReturn,
  googleAuthEnabled,
  googleAuthorizeUrl,
  googleReturn,
  takeGoogleReturn,
} from "./google-auth.ts";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "hosted",
  today: "2026-11-21",
  prefs: { easy_pace: "", intro_seen: null },
};

function memoryStorage() {
  const bag = new Map<string, string>();
  return {
    getItem: (key: string) => bag.get(key) ?? null,
    setItem: (key: string, value: string) => {
      bag.set(key, value);
    },
    removeItem: (key: string) => {
      bag.delete(key);
    },
  };
}

async function withFetch(fetchImpl: typeof fetch, run: () => Promise<void>): Promise<void> {
  const previous = globalThis.fetch;
  globalThis.fetch = fetchImpl;
  try {
    await run();
  } finally {
    globalThis.fetch = previous;
  }
}

describe("google auth flag", () => {
  it("stays off unless the flag is true or 1", () => {
    assert.equal(googleAuthEnabled(undefined), false);
    assert.equal(googleAuthEnabled(""), false);
    assert.equal(googleAuthEnabled("false"), false);
    assert.equal(googleAuthEnabled("yes"), false);
    assert.equal(googleAuthEnabled(" TRUE "), true);
    assert.equal(googleAuthEnabled("1"), true);
  });

  it("follows only a Supabase Google authorize URL", () => {
    const live = "https://abcd.supabase.co/auth/v1/authorize?provider=google&redirect_to=https%3A%2F%2Fwww.riorunning.com%2Fauth%2Fcallback";
    assert.equal(googleAuthorizeUrl(live), live);
    assert.equal(googleAuthorizeUrl("http://127.0.0.1:54321/auth/v1/authorize?provider=google"), "http://127.0.0.1:54321/auth/v1/authorize?provider=google");
    assert.equal(googleAuthorizeUrl("https://evil.example/auth/v1/authorize?provider=google"), "");
    assert.equal(googleAuthorizeUrl("https://abcd.supabase.co/auth/v1/authorize?provider=github"), "");
    assert.equal(googleAuthorizeUrl("not a url"), "");
  });

  it("reads the code from the query or the hash, and keeps it for a remount", () => {
    const previous = globalThis.sessionStorage;
    Object.defineProperty(globalThis, "sessionStorage", { value: memoryStorage(), configurable: true });
    try {
      clearGoogleReturn();
      assert.deepEqual(googleReturn("?code=abc&flow=flow-1", ""), { code: "abc", flow: "flow-1", error: "" });
      assert.equal(googleReturn("", "#error=access_denied&error_description=no").error, "access_denied");
      const kept = takeGoogleReturn("?code=abc&flow=flow-1", "");
      assert.equal(kept.code, "abc");
      assert.equal(takeGoogleReturn("", "").code, "abc");
      clearGoogleReturn();
      assert.equal(takeGoogleReturn("", "").code, "");
      assert.equal(GOOGLE_FAILED.includes("Google"), true);
    } finally {
      Object.defineProperty(globalThis, "sessionStorage", { value: previous, configurable: true });
    }
  });

  it("the button is gated and a new Google session uses the email landing", () => {
    const screen = readFileSync(new URL("../components/AuthScreen.tsx", import.meta.url), "utf8");
    const callback = readFileSync(new URL("../components/GoogleCallback.tsx", import.meta.url), "utf8");
    assert.match(screen, /if \(!googleAuthEnabled\(\)\) return null/);
    assert.match(screen, /Continue with Google/);
    assert.equal(screen.includes("GOOGLE_CLIENT"), false);
    assert.match(callback, /destinationAfterSignIn\(signedIn!\)/);
    assert.match(callback, /api\.googleFinish\(back\.code, back\.flow\)/);
    const flow = readFileSync(new URL("../../api/account_flow.py", import.meta.url), "utf8");
    assert.match(flow, /origin \+ "\/auth\/callback"/);
  });
});

describe("google finish", { concurrency: false }, () => {
  it("does not reuse a signed-out session that is still in flight", async () => {
    let releaseFirst: (() => void) | null = null;
    let sessionCalls = 0;
    await withFetch(async (url) => {
      const path = String(url);
      if (path.includes("/auth/sign-out")) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      if (path.includes("/auth/google/callback")) {
        return new Response(JSON.stringify({ email: athlete.email, display_name: "Ada", kind: "hosted" }), { status: 200 });
      }
      if (path.includes("/auth/session")) {
        sessionCalls += 1;
        if (sessionCalls === 1) {
          return new Promise((resolve) => {
            releaseFirst = () => resolve(new Response(JSON.stringify({ signed_in: false }), { status: 200 }));
          });
        }
        return new Response(JSON.stringify(athlete), { status: 200 });
      }
      return new Response(JSON.stringify({ detail: "no" }), { status: 404 });
    }, async () => {
      await api.signOut();
      const first = refreshSession();
      await api.googleFinish("code-1", "flow-1");
      const second = await refreshSession();
      assert.equal(second.status, "in");
      assert.equal(second.athlete?.email, "ada@example.com");
      assert.equal(sessionCalls, 2);
      if (!releaseFirst) throw new Error("the first session read never started");
      releaseFirst();
      const stale = await first;
      assert.equal(stale.status, "out");
    });
  });
});
