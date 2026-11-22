import assert from "node:assert/strict";
import test from "node:test";
import { SIGN_IN_NOTES, signInNotice } from "./sign-in-notes.ts";

test("only the note's own keys are shown", () => {
  assert.equal(signInNotice("password-updated"), SIGN_IN_NOTES["password-updated"]);
  assert.equal(signInNotice("google-failed"), "Google sign-in could not be finished. Try again.");
  assert.equal(signInNotice("session-stuck"), SIGN_IN_NOTES["session-stuck"]);
  assert.equal(signInNotice(""), "");
  assert.equal(signInNotice(null), "");
  assert.equal(signInNotice("missing"), "");
});

test("inherited keys are not sign-in notes", () => {
  assert.equal(signInNotice("__proto__"), "");
  assert.equal(signInNotice("constructor"), "");
  assert.equal(signInNotice("toString"), "");
  assert.equal(Object.hasOwn(SIGN_IN_NOTES, "__proto__"), false);
  assert.equal(Object.hasOwn(SIGN_IN_NOTES, "constructor"), false);
  assert.equal(Object.hasOwn(SIGN_IN_NOTES, "toString"), false);
});
