"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { ApiError, afterSignIn, api, confirmOnce } from "@/lib/api";
import { UNCONFIRMED } from "@/lib/auth-copy";
import { confirmFromLocation, confirmRead } from "@/lib/confirm-link";
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
}: {
  id: string;
  name: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [shown, setShown] = useState(false);
  return (
    <div className="rio-password">
      <input
        id={id}
        name={name}
        type={shown ? "text" : "password"}
        autoComplete={autoComplete}
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
    <div className="auth-screen">
      <main className="rio-auth-card">
        <header className="rio-hero rio-auth-hero">
          <p className="rio-synthetic">RIO</p>
          <h1>{title}</h1>
          {subtitle ? <p className="rio-range">{subtitle}</p> : null}
        </header>
        {notice ? <p className="rio-settings-note">{notice}</p> : null}
        {error ? <p className="rio-error">{error}</p> : null}
        {children}
      </main>
      <PhotoCredit>Photo by Steve Pancrate on Pexels</PhotoCredit>
      <Footer onPhoto />
    </div>
  );
}

export function SignInScreen() {
  const router = useRouter();
  const { status, refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [unconfigured, setUnconfigured] = useState(false);

  useEffect(() => {
    const note = new URLSearchParams(window.location.search).get("note");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (note) setNotice(note);
  }, []);

  useEffect(() => {
    if (status === "in") router.replace("/");
  }, [status, router]);

  useEffect(() => {
    let live = true;
    void api.accountMode().then((body) => {
      if (!live) return;
      setForgot(body.mode === "hosted");
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
      const stuck = afterSignIn(await refresh());
      if (stuck) {
        setError(stuck);
        return;
      }
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Email or password does not match.");
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
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="text" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
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
      await refresh();
      router.replace("/");
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
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="name">Name</label>
        <input id="name" name="name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} />
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="text" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label htmlFor="password">Password</label>
        <PasswordField
          id="password"
          name="password"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
        />
        <button className="rio-primary" type="submit" disabled={busy}>
          Create account
        </button>
      </form>
      {localFile ? <p className="rio-settings-note">First name is enough. At least 8 characters. Saved on this machine.</p> : null}
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
    let live = true;
    void api.accountMode().then((body) => {
      if (!live) return;
      if (body.mode !== "hosted") router.replace("/sign-in");
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
        <input id="email" name="email" type="text" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
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
      window.location.replace("/reset-password" + window.location.search + window.location.hash);
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
