import assert from "node:assert/strict";
import test from "node:test";
import { recoveryFromLocation, recoveryReady } from "./reset-link.ts";

test("the query token matches what Streamlit reads", () => {
  const hash = recoveryFromLocation("?token_hash=hashed&type=recovery", "");
  assert.equal(hash.token, "hashed");
  assert.equal(hash.type, "recovery");
  assert.equal(recoveryReady(hash), true);

  const plain = recoveryFromLocation("?reset=password&token=plain-token", "");
  assert.equal(plain.token, "plain-token");
  assert.equal(plain.reset, "password");
  assert.equal(recoveryReady(plain), true);

  const both = recoveryFromLocation("?token=plain&token_hash=hashed", "");
  assert.equal(both.token, "hashed");
});

test("a hash fragment is read, and the query wins when both are set", () => {
  const fragment = recoveryFromLocation(
    "",
    "#access_token=access&refresh_token=refresh&token_type=bearer&type=recovery&expires_in=3600",
  );
  assert.equal(fragment.token, "");
  assert.equal(fragment.accessToken, "access");
  assert.equal(fragment.refreshToken, "refresh");
  assert.equal(fragment.type, "recovery");
  assert.equal(recoveryReady(fragment), true);

  const named = recoveryFromLocation("?reset=password", "#token_hash=from-hash&type=recovery");
  assert.equal(named.token, "from-hash");
  assert.equal(named.reset, "password");

  const queryWins = recoveryFromLocation("?token_hash=from-query", "#token_hash=from-hash");
  assert.equal(queryWins.token, "from-query");
});

test("a session fragment without type=recovery is not a reset", () => {
  const signup = recoveryFromLocation("", "#access_token=access&refresh_token=refresh&type=signup");
  assert.equal(recoveryReady(signup), false);
  const empty = recoveryFromLocation("", "");
  assert.equal(recoveryReady(empty), false);
});
