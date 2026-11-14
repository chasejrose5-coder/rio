import assert from "node:assert/strict";
import test from "node:test";
import {
  CONFIRM_EMAIL,
  CONFIRM_INVALID,
  CONFIRM_SIGNUP,
  MAIL_RATE,
  RESEND_SENT,
  RESET_SENT,
  UNCONFIRMED,
} from "./auth-copy.ts";

test("mail sentences stay the ones the API returns", () => {
  assert.equal(UNCONFIRMED, "Check your email to confirm your account, then log in.");
  assert.equal(RESEND_SENT, "If that address still needs confirmation, we sent another email.");
  assert.equal(RESET_SENT, "Check your email for the reset link.");
  assert.equal(MAIL_RATE, "Too many attempts. Wait a few minutes and try again.");
  assert.equal(CONFIRM_INVALID, "That confirmation link is no longer valid.");
  assert.equal(CONFIRM_SIGNUP, "Email confirmed. You can log in.");
  assert.match(CONFIRM_EMAIL, /second email is still waiting/);
});
