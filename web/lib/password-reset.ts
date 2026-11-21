/** Forgot password stays hidden until Supabase is sending mail.

`NEXT_PUBLIC_PASSWORD_RESET_ENABLED` is the string `true` after Resend is
Supabase's SMTP server. Anything else, including an unset variable, keeps
the link off. The value is public. It is not a key. See
`docs/resend-email-setup.md`.
*/

export function passwordResetEnabled(value?: string | null): boolean {
  const raw = value === undefined ? process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED : value;
  return (raw ?? "").trim().toLowerCase() === "true";
}

/** A hosted account can email a reset. The flag still has to be on. */
export function showForgotPassword(mode: string, enabled?: boolean): boolean {
  return mode === "hosted" && (enabled ?? passwordResetEnabled());
}
