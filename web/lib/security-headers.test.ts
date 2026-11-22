import assert from "node:assert/strict";
import test from "node:test";
import { POST } from "../app/csp-report/route.ts";
import { DOCUMENT_SECURITY_HEADERS, SITE_ORIGIN, documentSecurityRoutes } from "./security-headers.ts";

test("html security headers enforce CSP, allow Google sign-in, and report violations", () => {
  const headers = Object.fromEntries(DOCUMENT_SECURITY_HEADERS.map((item) => [item.key, item.value]));
  assert.equal(headers["Content-Security-Policy-Report-Only"], undefined);
  const policy = headers["Content-Security-Policy"];
  assert.match(policy, /default-src 'self'/);
  assert.match(policy, /frame-ancestors 'none'/);
  assert.match(policy, /font-src 'self' https:\/\/fonts\.gstatic\.com/);
  assert.match(policy, /style-src 'self' 'unsafe-inline' https:\/\/accounts\.google\.com/);
  assert.match(policy, /https:\/\/vercel\.live/);
  assert.match(policy, /report-uri \/csp-report/);
  assert.match(policy, /report-to csp/);
  assert.equal(headers["Reporting-Endpoints"], 'csp="/csp-report"');
  for (const directive of ["script-src", "frame-src", "connect-src", "style-src"]) {
    const rule = policy.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${directive} `));
    assert.ok(rule, directive);
    assert.match(rule, /https:\/\/accounts\.google\.com/);
  }
  assert.equal(policy.includes("unsafe-eval"), false);
  assert.equal(POST().status, 204);
  assert.equal(headers["X-Content-Type-Options"], "nosniff");
  assert.equal(headers["Referrer-Policy"], "strict-origin-when-cross-origin");
  assert.match(headers["Permissions-Policy"], /camera=\(\)/);
  assert.equal(headers["Permissions-Policy"].includes("browsing-topics"), false);
  assert.match(headers["Permissions-Policy"], /microphone=\(\)/);
  assert.match(headers["Permissions-Policy"], /geolocation=\(\)/);
  assert.match(headers["Permissions-Policy"], /payment=\(\)/);
  assert.match(headers["Permissions-Policy"], /usb=\(\)/);
  assert.equal(headers["X-Frame-Options"], "DENY");
  assert.equal(headers["Access-Control-Allow-Origin"], SITE_ORIGIN);
  assert.equal(headers["Access-Control-Allow-Origin"].includes("*"), false);
  const sources = documentSecurityRoutes(false).map((item) => item.source);
  assert.equal(sources.includes("/api/:path*"), false);
  assert.ok(sources.includes("/"));
  const production = documentSecurityRoutes(false)[0]?.headers.find((item) => item.key === "Content-Security-Policy")?.value || "";
  const development = documentSecurityRoutes(true)[0]?.headers.find((item) => item.key === "Content-Security-Policy")?.value || "";
  assert.equal(production.includes("unsafe-eval"), false);
  assert.equal(production.includes("localhost"), false);
  assert.match(development, /unsafe-eval/);
  assert.match(development, /http:\/\/localhost:8000/);
});
