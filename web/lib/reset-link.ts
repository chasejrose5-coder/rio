/** Tokens on a Supabase recovery link.

Streamlit reads `token_hash` or `token` from the query, and opens the form
when `reset=password` or `type=recovery`. Supabase also puts the session in
the hash after it verifies the mail: `access_token`, `refresh_token`, and
`type=recovery`. The same names are accepted in either place. The query wins
when both name a value. `token_hash` wins over `token`.
*/

export type RecoveryLink = {
  token: string;
  accessToken: string;
  refreshToken: string;
  type: string;
  reset: string;
};

function paramsOf(raw: string): URLSearchParams {
  const text = raw.startsWith("?") || raw.startsWith("#") ? raw.slice(1) : raw;
  return new URLSearchParams(text);
}

function first(query: URLSearchParams, fragment: URLSearchParams, name: string): string {
  return query.get(name) || fragment.get(name) || "";
}

export function recoveryFromLocation(search: string, hash: string): RecoveryLink {
  const query = paramsOf(search);
  const fragment = paramsOf(hash);
  return {
    token: first(query, fragment, "token_hash") || first(query, fragment, "token"),
    accessToken: first(query, fragment, "access_token"),
    refreshToken: first(query, fragment, "refresh_token"),
    type: first(query, fragment, "type"),
    reset: first(query, fragment, "reset"),
  };
}

/** A token_hash can be verified on its own. A hash session needs type=recovery. */
export function recoveryReady(link: RecoveryLink): boolean {
  if (link.token) return true;
  return link.type === "recovery" && Boolean(link.accessToken) && Boolean(link.refreshToken);
}
