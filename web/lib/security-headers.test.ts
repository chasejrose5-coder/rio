import assert from "node:assert/strict";
import test from "node:test";
import { DOCUMENT_SECURITY_HEADERS, SITE_ORIGIN, documentSecurityRoutes } from "./security-headers.ts";

test("html security headers are report-only except framing, and the origin is not a wildcard", () => {
  const headers = Object.fromEntries(DOCUMENT_SECURITY_HEADERS.map((item) => [item.key, item.value]));
  assert.equal(headers["Content-Security-Policy"], "frame-ancestors 'none'");
  assert.match(headers["Content-Security-Policy-Report-Only"], /default-src 'self'/);
  assert.match(headers["Content-Security-Policy-Report-Only"], /font-src 'self'/);
  assert.match(headers["Content-Security-Policy-Report-Only"], /https:\/\/vercel\.live/);
  const report = headers["Content-Security-Policy-Report-Only"];
  for (const directive of ["script-src", "frame-src", "connect-src"]) {
    const rule = report.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${directive} `));
    assert.ok(rule, directive);
    assert.match(rule, /https:\/\/accounts\.google\.com/);
  }
  assert.equal(headers["Content-Security-Policy-Report-Only"].includes("unsafe-eval"), false);
  assert.equal(headers["X-Content-Type-Options"], "nosniff");
  assert.equal(headers["Referrer-Policy"], "strict-origin-when-cross-origin");
  assert.match(headers["Permissions-Policy"], /camera=\(\)/);
  assert.equal(headers["X-Frame-Options"], "DENY");
  assert.equal(headers["Access-Control-Allow-Origin"], SITE_ORIGIN);
  assert.equal(headers["Access-Control-Allow-Origin"].includes("*"), false);
  const sources = documentSecurityRoutes().map((item) => item.source);
  assert.equal(sources.includes("/api/:path*"), false);
  assert.ok(sources.includes("/"));
});
