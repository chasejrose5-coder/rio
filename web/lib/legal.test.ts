import assert from "node:assert/strict";
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
    "seven-day",
    "does not send an email that the delete finished",
    "sessionStorage",
    "800",
  ]) {
    assert.match(text, new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.equal(text.includes("goal probability"), true);
  assert.equal(/we sell your data/i.test(text), false);
});

test("the terms draft does not invent a contract", () => {
  const text = legalPlainText(TERMS);
  assert.match(text, /does not make it a contract/);
  assert.match(text, /activity:read_all/);
  assert.match(text, /any runner/);
  assert.equal(/you agree to/i.test(text), false);
});
