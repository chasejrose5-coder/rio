import assert from "node:assert/strict";
import test from "node:test";
import { confirmFromLocation, confirmRead } from "./confirm-link.ts";

test("a signup token_hash is ready, and the query wins over the hash", () => {
  const query = confirmFromLocation("?token_hash=hashed&type=signup", "");
  assert.equal(query.token, "hashed");
  assert.equal(query.type, "signup");
  assert.equal(confirmRead(query), "ready");

  const both = confirmFromLocation("?token_hash=from-query&type=email", "#token_hash=from-hash&type=signup");
  assert.equal(both.token, "from-query");
  assert.equal(both.type, "email");
  assert.equal(confirmRead(both), "ready");
});

test("an email-change session fragment is ready", () => {
  const fragment = confirmFromLocation(
    "",
    "#access_token=access&refresh_token=refresh&type=email_change",
  );
  assert.equal(fragment.accessToken, "access");
  assert.equal(fragment.refreshToken, "refresh");
  assert.equal(confirmRead(fragment), "ready");
});

test("a recovery fragment is not confirmed here", () => {
  const recovery = confirmFromLocation("", "#access_token=access&refresh_token=refresh&type=recovery");
  assert.equal(confirmRead(recovery), "recovery");
});

test("an empty page is waiting, and an expired link is invalid", () => {
  assert.equal(confirmRead(confirmFromLocation("", "")), "missing");
  const expired = confirmFromLocation("?error=access_denied&error_code=otp_expired", "");
  assert.equal(confirmRead(expired), "invalid");
  const limited = confirmFromLocation("?error_code=over_request_rate_limit", "");
  assert.equal(confirmRead(limited), "rate");
  const half = confirmFromLocation("?type=signup", "");
  assert.equal(confirmRead(half), "invalid");
});
