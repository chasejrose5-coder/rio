import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { apiBase } from "./api.ts";
import { apiOrigin, apiProxyRewrites, applyApiRewrite } from "./deploy-proxy.ts";

test("an unset origin does not rewrite, so local dev stays on port 8000", () => {
  assert.deepEqual(apiProxyRewrites(undefined), []);
  assert.deepEqual(apiProxyRewrites(null), []);
  assert.deepEqual(apiProxyRewrites(""), []);
  assert.deepEqual(apiProxyRewrites("   "), []);
});

test("the rewrite strips /api and keeps the query on the FastAPI path", () => {
  const origin = "https://rio-api.onrender.com";
  const rewrites = apiProxyRewrites(`${origin}/`);
  assert.deepEqual(rewrites, [
    { source: "/api/:path*", destination: "https://rio-api.onrender.com/:path*" },
  ]);
  assert.equal(applyApiRewrite(rewrites, "/api/health"), "https://rio-api.onrender.com/health");
  assert.equal(applyApiRewrite(rewrites, "/api/auth/me"), "https://rio-api.onrender.com/auth/me");
  assert.equal(
    applyApiRewrite(rewrites, "/api/strava/callback?code=abc&state=strava%3A1"),
    "https://rio-api.onrender.com/strava/callback?code=abc&state=strava%3A1",
  );
  assert.equal(applyApiRewrite(rewrites, "/api/plan?month=2026-11"), "https://rio-api.onrender.com/plan?month=2026-11");
  assert.equal(applyApiRewrite(rewrites, "/settings"), null);
  assert.equal(applyApiRewrite(rewrites, "/api"), null);
  assert.equal(applyApiRewrite(rewrites, "/api/../health"), null);
});

test("a bad origin is refused", () => {
  for (const raw of [
    "*",
    "https://*",
    "https://user:secret@rio-api.onrender.com",
    "https://rio-api.onrender.com/health",
    "https://rio-api.onrender.com?x=1",
    "ftp://rio-api.onrender.com",
    "rio-api.onrender.com",
    "https://rio-api.onrender.com/not-a-host",
    "https://rio api.onrender.com",
  ]) {
    assert.equal(apiOrigin(raw), null, raw);
    assert.deepEqual(apiProxyRewrites(raw), [], raw);
  }
  assert.equal(apiOrigin("http://127.0.0.1:8000"), "http://127.0.0.1:8000");
});

test("NEXT_PUBLIC_RIO_API_URL=/api stays on the page origin", () => {
  const previous = process.env.NEXT_PUBLIC_RIO_API_URL;
  process.env.NEXT_PUBLIC_RIO_API_URL = "/api/";
  try {
    assert.equal(apiBase(), "/api");
    const rewrites = apiProxyRewrites("https://rio-api.onrender.com");
    assert.equal(applyApiRewrite(rewrites, `${apiBase()}/health`), "https://rio-api.onrender.com/health");
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_RIO_API_URL;
    else process.env.NEXT_PUBLIC_RIO_API_URL = previous;
  }
});

test("next.config applies that rewrite and does not bake a host", () => {
  const source = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
  assert.match(source, /apiProxyRewrites\(process\.env\.RIO_API_ORIGIN\)/);
  assert.equal(source.includes("onrender.com"), false);
  assert.equal(source.includes("vercel.app"), false);
  assert.equal(source.includes("supabase"), false);
});
