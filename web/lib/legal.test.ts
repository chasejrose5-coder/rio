import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { DRAFT_NOTE, PRIVACY, TERMS, legalPlainText } from "./legal-copy.ts";

const pages = [PRIVACY, TERMS];

test("both drafts name the operator and stay unpublished", () => {
  assert.equal(DRAFT_NOTE, "For review. This page is not in effect yet.");
  assert.equal(DRAFT_NOTE.includes("Jay"), false);
  assert.equal(DRAFT_NOTE.includes("Chase"), false);
  assert.equal(DRAFT_NOTE.includes("["), false);
  for (const page of pages) {
    const text = legalPlainText(page);
    assert.match(text, /DRAFT|draft/);
    assert.match(text, /not in effect/);
    assert.match(text, /Chase Rose, an individual/);
    assert.match(text, /The legal and privacy contact is riorunning\.app@gmail\.com/);
    assert.match(text, /The governing law chosen here is the law of the State of California/);
    assert.equal(text.includes("[COMPANY NAME]"), false);
    assert.equal(text.includes("[CONTACT EMAIL]"), false);
    assert.equal(text.includes("chasejrose5"), false);
    assert.equal(text.includes("Inc."), false);
    assert.equal(text.includes("mailing address"), false);
    assert.equal(text.includes("street address"), false);
    assert.equal(/\bcourt\b/i.test(text), false);
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
    "Delete my account calls Strava's deauthorize endpoint with the stored token",
    "Strava may monitor and collect usage data",
    "does not send an email that the delete finished",
    "sessionStorage",
    "800",
  ]) {
    assert.match(text, new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.equal(text.includes("goal probability"), true);
  assert.equal(/account deletion does not call Strava/i.test(text), false);
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

test("the privacy draft states the age line and drops the filled-in open items", () => {
  const text = legalPlainText(PRIVACY);
  assert.match(text, /RIO is not directed to children under 13/);
  assert.match(text, /If RIO learns that a user is under 13, the account will be deleted on request/);
  assert.match(text, /does not ask for a birth date/);
  assert.equal(text.includes("Still open"), false);
  assert.equal(/not decided/i.test(text), false);
});

test("the terms draft states the age minimum and leaves the open product terms", () => {
  const text = legalPlainText(TERMS);
  assert.match(text, /Users must be at least 13/);
  assert.match(text, /does not ask for a birth date and does not block signup by age/);
  assert.match(text, /No price, warranty, liability cap, or refund rule is decided here/);
  assert.match(text, /No warranty, liability cap, or refund rule is stated, because none is decided/);
  assert.match(text, /No age rule is enforced by the signup form/);
  assert.equal(text.includes("age minimum"), false);
  assert.equal(text.includes("street address"), false);
});

test("the terms draft does not invent a contract", () => {
  const text = legalPlainText(TERMS);
  assert.match(text, /does not make it a contract/);
  assert.match(text, /activity:read_all/);
  assert.match(text, /any runner/);
  assert.equal(/you agree to/i.test(text), false);
});
