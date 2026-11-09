"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const SIGNUP_FAILED = "The account could not be created.";

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
    void api.googleConfigured().then((configured) => {
      if (live) setForgot(configured);
    });
    return () => {
      live = false;
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.signIn(email, password);
      await refresh();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Email or password does not match.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Log in" subtitle="Use your email and password." error={error} notice={notice}>
      <form onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
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

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api.signUp(name, email, password);
      if (created.confirm) {
        setError(SIGNUP_FAILED);
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

  return (
    <AuthFrame title="Create account" error={error}>
      <form onSubmit={onSubmit}>
        <label htmlFor="name">Name</label>
        <input id="name" name="name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} required />
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <button className="rio-primary" type="submit" disabled={busy}>
          Create account
        </button>
      </form>
      <p className="rio-settings-note">First name is enough. At least 8 characters.</p>
      <Link className="rio-secondary" href="/sign-in">
        Back to log in
      </Link>
    </AuthFrame>
  );
}

export function ForgotScreen() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const sent = await api.forgot(email);
      setNote(sent.message || "Check your email for the reset link.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The reset email could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Forgot password" subtitle="We will email you a reset link." error={error}>
      {note ? <p className="rio-settings-note">{note}</p> : null}
      <form onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <button className="rio-primary" type="submit" disabled={busy}>
          Send reset email
        </button>
      </form>
      <Link className="rio-secondary" href="/sign-in">
        Back to log in
      </Link>
    </AuthFrame>
  );
}

export function ResetScreen({ token }: { token: string }) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const saved = await api.reset(token, password);
      router.replace(`/sign-in?note=${encodeURIComponent(saved.message || "Password updated. Log in with the new one.")}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That reset link is no longer valid.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="New password" error={error || (token ? "" : "That reset link is no longer valid.")}>
      <form onSubmit={onSubmit}>
        <label htmlFor="password">New password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <button className="rio-primary" type="submit" disabled={busy || !token}>
          Save password
        </button>
      </form>
    </AuthFrame>
  );
}
