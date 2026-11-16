"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

/** Shown once a visit has been waiting long enough to be a cold free-tier wake. */
export function WakeHint() {
  const { status } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (status !== "unreachable") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setShow(false);
      return;
    }
    const timer = window.setTimeout(() => setShow(true), 2000);
    return () => window.clearTimeout(timer);
  }, [status]);

  if (!show || status !== "unreachable") return null;
  return (
    <p className="rio-note">
      The server is waking up. After a quiet stretch the free host can take about a minute.
    </p>
  );
}

/** The signed-in shell while a route is still choosing Home or Start. */
export function LoadingScreen({ label = "Loading", onRetry }: { label?: string; onRetry?: () => void }) {
  return (
    <div className="rio-loading">
      <header className="rio-nav">
        <div className="rio-nav-row">
          <span className="rio-brand">RIO</span>
        </div>
      </header>
      <main>
        <p className="rio-wait">{label}</p>
        <WakeHint />
        {onRetry ? (
          <button type="button" className="rio-primary" onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </main>
    </div>
  );
}
