import assert from "node:assert/strict";
import test from "node:test";
import { passwordResetEnabled, showForgotPassword } from "./password-reset.ts";

test("only the string true turns password reset on", () => {
  assert.equal(passwordResetEnabled("true"), true);
  assert.equal(passwordResetEnabled("TRUE"), true);
  assert.equal(passwordResetEnabled(" true "), true);
  assert.equal(passwordResetEnabled("false"), false);
  assert.equal(passwordResetEnabled("1"), false);
  assert.equal(passwordResetEnabled("yes"), false);
  assert.equal(passwordResetEnabled(""), false);
  assert.equal(passwordResetEnabled(null), false);
});

test("an unset variable stays off", () => {
  const previous = process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED;
  delete process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED;
  try {
    assert.equal(passwordResetEnabled(), false);
    process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED = "true";
    assert.equal(passwordResetEnabled(), true);
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED;
    else process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED = previous;
  }
});

test("the link needs a hosted account and the flag", () => {
  assert.equal(showForgotPassword("hosted", true), true);
  assert.equal(showForgotPassword("hosted", false), false);
  assert.equal(showForgotPassword("local", true), false);
  assert.equal(showForgotPassword("unconfigured", true), false);
});
