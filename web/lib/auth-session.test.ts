import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { ApiError, API_TIMEOUT_MS, SESSION_STUCK, afterSignIn, api, refreshSession, signedOutProbe } from "./api.ts";
import type { Athlete } from "./types.ts";

const athlete: Athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "hosted",
  today: "2026-11-11",
  prefs: {},
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

describe("refresh session", { concurrency: false }, () => {
  it("a 500 from /auth/me ends loading", async () => {
    await withFetch(async () => new Response(JSON.stringify({ detail: "down" }), { status: 500 }), async () => {
      const result = await refreshSession();
      assert.equal(result.athlete, null);
      assert.equal(result.status, "out");
    });
  });

  it("a timed-out fetch is ApiError 0 and stays on the wake screen", async () => {
    const source = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
    assert.match(source, /signal:\s*AbortSignal\.timeout\(API_TIMEOUT_MS\)/);
    assert.equal(API_TIMEOUT_MS, 60_000);
    let timeoutMs = 0;
    const original = AbortSignal.timeout;
    AbortSignal.timeout = ((ms: number) => {
      timeoutMs = ms;
      return original.call(AbortSignal, ms);
    }) as typeof AbortSignal.timeout;
    try {
      await withFetch(async (_url, init) => {
        assert.ok(init?.signal);
        throw new DOMException("The operation was aborted due to timeout", "TimeoutError");
      }, async () => {
        await assert.rejects(api.me(), (error: unknown) => {
          assert.ok(error instanceof ApiError);
          assert.equal(error.status, 0);
          return true;
        });
        const result = await refreshSession();
        assert.equal(result.athlete, null);
        assert.equal(result.status, "unreachable");
        assert.equal(timeoutMs, API_TIMEOUT_MS);
      });
    } finally {
      AbortSignal.timeout = original;
    }
  });

  it("parallel session reads share one request, and a write drops the cache", async () => {
    let calls = 0;
    await withFetch(async (_url, init) => {
      calls += 1;
      const method = (init?.method || "GET").toUpperCase();
      if (method !== "GET") return new Response(JSON.stringify({ ok: true }), { status: 200 });
      await new Promise((resolve) => setTimeout(resolve, 20));
      return new Response(JSON.stringify(athlete), { status: 200 });
    }, async () => {
      await api.signOut();
      calls = 0;
      const [first, second] = await Promise.all([api.me(), api.me()]);
      assert.equal(calls, 1);
      assert.equal(first.email, second.email);
      await api.signOut();
      await api.me();
      assert.equal(calls, 3);
    });
  });

  it("a signed-out probe is 200 and does not call /auth/me", async () => {
    const urls: string[] = [];
    await withFetch(async (url) => {
      urls.push(String(url));
      return new Response(JSON.stringify({ signed_in: false }), { status: 200 });
    }, async () => {
      await api.signOut();
      urls.length = 0;
      const result = await refreshSession();
      assert.equal(result.status, "out");
      assert.equal(result.athlete, null);
      assert.equal(signedOutProbe({ signed_in: false }), true);
      assert.equal(urls.length, 1);
      assert.match(urls[0], /\/auth\/session$/);
    });
  });

  it("an empty session body falls back to /auth/me", async () => {
    const urls: string[] = [];
    await withFetch(async (url) => {
      urls.push(String(url));
      if (String(url).endsWith("/auth/session")) return new Response(JSON.stringify({}), { status: 200 });
      return new Response(JSON.stringify(athlete), { status: 200 });
    }, async () => {
      await api.signOut();
      urls.length = 0;
      const result = await refreshSession();
      assert.equal(result.status, "in");
      assert.equal(result.athlete?.email, "ada@example.com");
      assert.match(urls[1], /\/auth\/me$/);
    });
  });

  it("a missing session route falls back to /auth/me", async () => {
    const urls: string[] = [];
    await withFetch(async (url) => {
      urls.push(String(url));
      if (String(url).endsWith("/auth/session")) {
        return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
      }
      return new Response(JSON.stringify(athlete), { status: 200 });
    }, async () => {
      await api.signOut();
      urls.length = 0;
      const result = await refreshSession();
      assert.equal(result.status, "in");
      assert.equal(result.athlete?.email, "ada@example.com");
      assert.match(urls[0], /\/auth\/session$/);
      assert.match(urls[1], /\/auth\/me$/);
    });
  });

  it("a signed-in athlete stays in", async () => {
    await withFetch(async () => new Response(JSON.stringify(athlete), { status: 200 }), async () => {
      await api.signOut();
      const result = await refreshSession();
      assert.equal(result.status, "in");
      assert.equal(result.athlete?.email, "ada@example.com");
    });
  });
});

describe("sign-in when refresh returns null", () => {
  it("stays on the page with a visible error", () => {
    assert.equal(afterSignIn(null), SESSION_STUCK);
    assert.equal(SESSION_STUCK, "Signed in, but the session didn't stick. Try again.");
    assert.equal(afterSignIn(athlete), null);
    const screen = readFileSync(new URL("../components/AuthScreen.tsx", import.meta.url), "utf8");
    assert.match(screen, /const signedIn = await refresh\(\)/);
    assert.match(screen, /const stuck = afterSignIn\(signedIn\)/);
    assert.match(screen, /setError\(stuck\)/);
    const signIn = screen.slice(screen.indexOf("async function onSubmit"), screen.indexOf("export function CreateAccountScreen"));
    const guard = signIn.indexOf("if (stuck)");
    const navigate = signIn.indexOf("destinationAfterSignIn(signedIn!)");
    assert.ok(guard !== -1 && navigate !== -1 && guard < navigate);
    assert.equal(signIn.includes('router.replace("/")'), false);
  });
});
