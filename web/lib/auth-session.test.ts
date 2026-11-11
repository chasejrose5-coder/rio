import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { ApiError, SESSION_STUCK, afterSignIn, api, refreshSession } from "./api.ts";
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

  it("a timed-out fetch is ApiError 0 and ends loading", async () => {
    const source = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
    assert.match(source, /signal:\s*AbortSignal\.timeout\(15000\)/);
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
        assert.equal(result.status, "out");
        assert.equal(timeoutMs, 15000);
      });
    } finally {
      AbortSignal.timeout = original;
    }
  });

  it("a signed-in athlete stays in", async () => {
    await withFetch(async () => new Response(JSON.stringify(athlete), { status: 200 }), async () => {
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
    assert.match(screen, /const stuck = afterSignIn\(await refresh\(\)\)/);
    assert.match(screen, /setError\(stuck\)/);
    const signIn = screen.slice(screen.indexOf("async function onSubmit"), screen.indexOf("export function CreateAccountScreen"));
    const guard = signIn.indexOf("if (stuck)");
    const navigate = signIn.indexOf('router.replace("/")');
    assert.ok(guard !== -1 && navigate !== -1 && guard < navigate);
  });
});
