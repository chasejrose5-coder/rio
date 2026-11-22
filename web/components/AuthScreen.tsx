"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { ApiError, afterSignIn, api, confirmOnce } from "@/lib/api";
import { UNCONFIRMED } from "@/lib/auth-copy";
import { confirmFromLocation, confirmRead } from "@/lib/confirm-link";
import { destinationAfterSignIn, warmDestinationReads } from "@/lib/enter";
import { GoogleIdentityButton } from "./GoogleIdentityButton";
import { GOOGLE_START_FAILED, googleAuthEnabled, googleAuthorizeUrl, googleClientId, googleGisHost } from "@/lib/google-auth";
import { passwordResetEnabled, showForgotPassword } from "@/lib/password-reset";
import { recoveryReady, type RecoveryLink } from "@/lib/reset-link";
import { useAuth } from "@/lib/auth";

const SIGNUP_FAILED = "The account could not be created.";
const RESET_INVALID = "That reset link is no longer valid.";

function PasswordField({
  id,
  name,
  autoComplete,
  value,
  onChange,
  describedBy,
}: {
  id: string;
  name: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
  describedBy?: string;
}) {
  const [shown, setShown] = useState(false);
  return (
    <div className="rio-password">
      <input
        id={id}
        name={name}
        type={shown ? "text" : "password"}
        autoComplete={autoComplete}
        aria-describedby={describedBy}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="rio-eye"
        aria-label={shown ? "Hide password" : "Show password"}
        onClick={() => setShown((current) => !current)}
      >
        <Eye open={shown} />
      </button>
    </div>
  );
}

function Eye({ open }: { open: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.7" />
      {open ? <path d="M4 5l16 14" stroke="currentColor" strokeWidth="1.7" /> : null}
    </svg>
  );
}

function ResendConfirmation({ email }: { email: string }) {
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const mail = emailProblem(email);
    if (mail) {
      setProblem(mail);
      return;
    }
    setBusy(true);
    setProblem("");
    setNote("");
    try {
      const sent = await api.resend(email.trim());
      setNote(sent.message || "If that address still needs confirmation, we sent another email.");
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "The confirmation email could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {note ? <p className="rio-settings-note">{note}</p> : null}
      {problem ? <p className="rio-error">{problem}</p> : null}
      <button type="button" className="rio-text-link" onClick={() => void send()} disabled={busy}>
        Resend confirmation email
      </button>
    </>
  );
}

function emailProblem(email: string): string {
  const text = email.trim();
  if (!text || text.split("@").length !== 2 || !text.split("@")[1]?.includes(".")) {
    return "Enter an email address.";
  }
  return "";
}

function signInProblem(email: string, password: string): string {
  return emailProblem(email) || (password ? "" : "Email or password does not match.");
}

function createProblem(name: string, email: string, password: string): string {
  if (!name.trim() || !/[A-Za-z]/.test(name)) return "Enter a name.";
  const mail = emailProblem(email);
  if (mail) return mail;
  if (password.length < 8) return "Use at least 8 characters.";
  return "";
}

function GoogleMark() {
  return (
    <svg className="rio-google-mark" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332z" />
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58z" />
    </svg>
  );
}

function GoogleRedirectButton({ onError }: { onError: (message: string) => void }) {
  const [busy, setBusy] = useState(false);

  async function start() {
    setBusy(true);
    onError("");
    try {
      const started = await api.googleStart();
      const url = googleAuthorizeUrl(started.url || "");
      if (!url) {
        onError(GOOGLE_START_FAILED);
        setBusy(false);
        return;
      }
      window.location.assign(url);
    } catch (caught) {
      onError(caught instanceof ApiError ? caught.message : GOOGLE_START_FAILED);
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="rio-secondary rio-google" onClick={() => void start()} disabled={busy}>
        <GoogleMark />
        Continue with Google
      </button>
    </>
  );
}

function GoogleContinue({ onError }: { onError: (message: string) => void }) {
  const enabled = googleAuthEnabled();
  const clientId = googleClientId();
  const [mode, setMode] = useState<"wait" | "gis" | "redirect">("wait");

  useEffect(() => {
    if (!enabled) return;
    const gis = clientId !== "" && googleGisHost(window.location.hostname);
    // The host is only known in the browser. The first paint stays a blank slot.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMode(gis ? "gis" : "redirect");
  }, [enabled, clientId]);

  if (!enabled) return null;
  return (
    <>
      {mode === "gis" ? (
        <GoogleIdentityButton clientId={clientId} onError={onError} onFail={() => setMode("redirect")} />
      ) : null}
      {mode === "redirect" ? <GoogleRedirectButton onError={onError} /> : null}
      {mode === "wait" ? <div className="rio-google-slot" /> : null}
      <p className="rio-auth-or">or</p>
    </>
  );
}

function AuthFrame({
  title,
  subtitle,
  error,
  notice,
  children,
}: {
  title: string;
  subtitle?: string;
  error?: string;
  notice?: string;
  children: React.ReactNode;
}) {
  return (
    <main className="auth-screen">
      <div className="rio-auth-card">
        <header className="rio-hero rio-auth-hero">
          <p className="rio-synthetic">RIO</p>
          <h1>{title}</h1>
          {subtitle ? <p className="rio-range">{subtitle}</p> : null}
        </header>
        {notice ? <p className="rio-settings-note">{notice}</p> : null}
        {error ? <p className="rio-error">{error}</p> : null}
        {children}
      </div>
      <PhotoCredit>Photo by Steve Pancrate on Pexels</PhotoCredit>
      <Footer onPhoto />
    </main>
  );
}

export function SignInScreen() {
  const router = useRouter();
  const { status, athlete, refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [unconfigured, setUnconfigured] = useState(false);
  const handoff = useRef(false);

  useEffect(() => {
    const note = new URLSearchParams(window.location.search).get("note");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (note) setNotice(note);
  }, []);

  useEffect(() => {
    if (handoff.current || status !== "in" || !athlete) return;
    let live = true;
    void destinationAfterSignIn(athlete)
      .then((path) => {
        if (live) router.replace(path);
      })
      .catch(() => {
        if (live) router.replace("/home");
      });
    return () => {
      live = false;
    };
  }, [status, athlete, router]);

  useEffect(() => {
    let live = true;
    void api.accountMode().then((body) => {
      if (!live) return;
      setForgot(showForgotPassword(body.mode));
      setUnconfigured(body.mode === "unconfigured");
    }).catch(() => {
      if (!live) return;
      setForgot(false);
      setUnconfigured(false);
    });
    return () => {
      live = false;
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problem = signInProblem(email, password);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.signIn(email, password);
      warmDestinationReads();
      handoff.current = true;
      const signedIn = await refresh();
      const stuck = afterSignIn(signedIn);
      if (stuck) {
        handoff.current = false;
        setError(stuck);
        return;
      }
      router.replace(await destinationAfterSignIn(signedIn!));
    } catch (caught) {
      handoff.current = false;
      setError(caught instanceof ApiError ? caught.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Log in" subtitle="Use your email and password." error={error} notice={notice}>
      {unconfigured ? (
        <div className="rio-setup-card">
          <p className="rio-mark-label">Accounts aren&apos;t set up yet</p>
          <p className="rio-note">Sign-in will open here after accounts are connected.</p>
        </div>
      ) : null}
      <GoogleContinue onError={setError} />
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label htmlFor="password">Password</label>
        <PasswordField
          id="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={setPassword}
        />
        <button className="rio-primary" type="submit" disabled={busy}>
          Log in
        </button>
      </form>
      {forgot ? (
        <Link className="rio-text-link" href="/forgot-password">
          Forgot password?
        </Link>
      ) : null}
      {error === UNCONFIRMED ? <ResendConfirmation email={email} /> : null}
      <Link className="rio-secondary" href="/create-account">
        Create account
      </Link>
    </AuthFrame>
  );
}

export function CreateAccountScreen() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sentTo, setSentTo] = useState("");
  const [localFile, setLocalFile] = useState(false);

  useEffect(() => {
    let live = true;
    void api.accountsHosted().then((hosted) => {
      if (live) setLocalFile(!hosted);
    });
    return () => {
      live = false;
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problem = createProblem(name, email, password);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await api.signUp(name, email, password);
      if (created.confirm) {
        setSentTo(email.trim());
        return;
      }
      warmDestinationReads();
      const signedIn = await refresh();
      if (!signedIn) {
        setError(SIGNUP_FAILED);
        return;
      }
      router.replace(await destinationAfterSignIn(signedIn));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : SIGNUP_FAILED);
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <AuthFrame title="Check your email" subtitle="Confirm your email, then log in.">
        <p className="rio-settings-note">
          We sent a confirmation link to {sentTo}. Open it, then log in.
        </p>
        <ResendConfirmation email={sentTo} />
        <Link className="rio-secondary" href="/sign-in">
          Back to log in
        </Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title="Create account" error={error}>
      <GoogleContinue onError={setError} />
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="name">Name</label>
        <input id="name" name="name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} />
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label htmlFor="password">Password</label>
        <PasswordField
          id="password"
          name="password"
          autoComplete="new-password"
          describedBy="password-hint"
          value={password}
          onChange={setPassword}
        />
        <p className="rio-field-hint" id="password-hint">At least 8 characters.</p>
        <button className="rio-primary" type="submit" disabled={busy}>
          Create account
        </button>
      </form>
      {localFile ? <p className="rio-settings-note">First name is enough. Saved on this machine.</p> : null}
      <Link className="rio-secondary" href="/sign-in">
        Back to log in
      </Link>
    </AuthFrame>
  );
}

export function ForgotScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!passwordResetEnabled()) {
      router.replace("/sign-in");
      return;
    }
    let live = true;
    void api.accountMode().then((body) => {
      if (!live) return;
      if (!showForgotPassword(body.mode)) router.replace("/sign-in");
      else setReady(true);
    }).catch(() => {
      if (live) router.replace("/sign-in");
    });
    return () => {
      live = false;
    };
  }, [router]);

  if (!ready) return <p className="rio-wait">Loading</p>;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problem = emailProblem(email);
    if (problem) {
      setError(problem);
      setNote("");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const sent = await api.forgot(email);
      setNote(sent.message || "Check your email for the reset link.");
    } catch (caught) {
      setNote("");
      setError(caught instanceof ApiError ? caught.message : "The reset email could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Forgot password" subtitle="We will email you a reset link." error={error}>
      {note ? <p className="rio-settings-note">{note}</p> : null}
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button className="rio-primary" type="submit" disabled={busy}>
          Send reset email
        </button>
      </form>
      {error === UNCONFIRMED ? <ResendConfirmation email={email} /> : null}
      <Link className="rio-secondary" href="/sign-in">
        Back to log in
      </Link>
    </AuthFrame>
  );
}

export function ResetScreen({ link }: { link: RecoveryLink }) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ready = recoveryReady(link);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!ready) {
      setError(RESET_INVALID);
      return;
    }
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const saved = await api.reset({
        token: link.token,
        password,
        access_token: link.token ? "" : link.accessToken,
        refresh_token: link.token ? "" : link.refreshToken,
        type: link.type,
      });
      router.replace(`/sign-in?note=${encodeURIComponent(saved.message || "Password updated. Log in with the new one.")}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : RESET_INVALID);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="New password" error={error || (ready ? "" : RESET_INVALID)}>
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="password">New password</label>
        <PasswordField
          id="password"
          name="password"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
        />
        <button className="rio-primary" type="submit" disabled={busy || !ready}>
          Save password
        </button>
      </form>
      {!ready || error === RESET_INVALID ? (
        <Link className="rio-secondary" href="/forgot-password">
          Send a new reset email
        </Link>
      ) : null}
    </AuthFrame>
  );
}

const CONFIRM_KEY = "rio-confirm-result";

type ConfirmView = { body: string; error: boolean; refreshed: boolean };

function keepConfirm(view: ConfirmView) {
  try {
    sessionStorage.setItem(CONFIRM_KEY, JSON.stringify(view));
  } catch {
    /* A blocked store still shows the sentence in this render. */
  }
  window.history.replaceState({}, "", "/confirm");
}

function keptConfirm(): ConfirmView | null {
  try {
    const raw = sessionStorage.getItem(CONFIRM_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ConfirmView>;
    if (typeof parsed.body !== "string" || typeof parsed.error !== "boolean") return null;
    return { body: parsed.body, error: parsed.error, refreshed: parsed.refreshed === true };
  } catch {
    return null;
  }
}

export function ConfirmScreen() {
  const [view, setView] = useState<ConfirmView | null>(null);

  useEffect(() => {
    const link = confirmFromLocation(window.location.search, window.location.hash);
    const read = confirmRead(link);
    if (read === "recovery") {
      window.location.replace("/update-password" + window.location.search + window.location.hash);
      return;
    }
    const show = (next: ConfirmView) => {
      keepConfirm(next);
      setView(next);
    };
    if (read === "missing") {
      // A stripped link remounts this page. The sentence from that link stays.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setView(
        keptConfirm() ?? {
          body: "Open the confirmation link in your email. It lands on this page.",
          error: false,
          refreshed: false,
        },
      );
      return;
    }
    if (read === "rate") {
      show({
        body: "Too many attempts. Wait a few minutes and try again.",
        error: true,
        refreshed: false,
      });
      return;
    }
    if (read !== "ready") {
      show({ body: "That confirmation link is no longer valid.", error: true, refreshed: false });
      return;
    }
    let live = true;
    void confirmOnce(link)
      .then((saved) => {
        if (!live) return;
        show({
          body: saved.message || "Email confirmed. You can log in.",
          error: false,
          refreshed: saved.refreshed === true,
        });
      })
      .catch((caught: unknown) => {
        if (!live) return;
        show({
          body: caught instanceof ApiError ? caught.message : "That confirmation link is no longer valid.",
          error: true,
          refreshed: false,
        });
      });
    return () => {
      live = false;
    };
  }, []);

  if (!view) return <p className="rio-wait">Loading</p>;
  return (
    <AuthFrame title="Confirm email" error={view.error ? view.body : ""} notice={view.error ? "" : view.body}>
      {view.refreshed ? (
        <Link className="rio-secondary" href="/settings">
          Back to Settings
        </Link>
      ) : null}
      <Link className="rio-secondary" href="/sign-in">
        Log in
      </Link>
    </AuthFrame>
  );
}
