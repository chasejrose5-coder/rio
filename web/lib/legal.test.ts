import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { DRAFT_NOTE, PRIVACY, TERMS, legalPlainText } from "./legal-copy.ts";

const pages = [PRIVACY, TERMS];

test("both drafts name the placeholders and stay unpublished", () => {
  for (const page of pages) {
    const text = legalPlainText(page);
    assert.match(text, /DRAFT|draft/);
    assert.match(DRAFT_NOTE, /Jay and Chase/);
    assert.match(text, /\[COMPANY NAME\]/);
    assert.match(text, /\[CONTACT EMAIL\]/);
    assert.equal(text.includes("chasejrose5"), false);
    assert.equal(text.includes("Inc."), false);
    assert.equal(/governed by the laws/i.test(text), false);
    assert.equal(/\d{1,5} .+(Street|Avenue|Blvd)/i.test(text), false);
  }
});

test("the privacy draft matches the account, cookie, and Strava read", () => {
  const text = legalPlainText(PRIVACY);
  for (const phrase of [
    "activity:read_all",
    "rio_hosted",
    "HttpOnly",
    "SameSite=Lax",
    "Supabase",
    "Delete my account",
    "deauthorize",
    "Strava may monitor and collect usage data",
    "does not send an email that the delete finished",
    "sessionStorage",
    "800",
  ]) {
    assert.match(text, new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.equal(text.includes("goal probability"), true);
  assert.equal(/we sell your data/i.test(text), false);
  for (const hidden of [
    "RIO_EXPLAIN_API_KEY",
    "RIO_EXPLAIN_MODEL",
    "RIO_EXPLAIN_BASE_URL",
    "RIO_INSIGHT_LOG_PATH",
    "insight_log",
    "strava_tokens",
    "app_sessions",
    "stretch_completions",
    "sore_spots",
    "strava_activities",
    "strava_oauth",
    "season_state",
    "seven-day",
    "GDPR",
    "section 6.2",
    "section 6.5",
    "section 7.3",
    "June 1, 2026",
  ]) {
    assert.equal(text.toLowerCase().includes(hidden.toLowerCase()), false, hidden);
  }
});

test("contents links and the legal wordmark are 44px targets", () => {
  const css = readFileSync(new URL("../app/legal.css", import.meta.url), "utf8");
  assert.match(css, /\.rio-legal-contents a[\s\S]*?min-height:\s*44px/);
  assert.match(css, /\.rio-legal-top a[\s\S]*?min-height:\s*44px/);
  assert.match(css, /size-adjust:/);
});

test("the terms draft does not invent a contract", () => {
  const text = legalPlainText(TERMS);
  assert.match(text, /does not make it a contract/);
  assert.match(text, /activity:read_all/);
  assert.match(text, /any runner/);
  assert.equal(/you agree to/i.test(text), false);
});
