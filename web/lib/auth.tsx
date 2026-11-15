"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, refreshSession } from "./api";
import type { Athlete } from "./types";

type Status = "loading" | "in" | "out" | "unreachable";

type AuthValue = {
  status: Status;
  athlete: Athlete | null;
  refresh: () => Promise<Athlete | null>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [athlete, setAthlete] = useState<Athlete | null>(null);

  const refresh = useCallback(async (): Promise<Athlete | null> => {
    const next = await refreshSession();
    setAthlete(next.athlete);
    setStatus(next.status);
    return next.athlete;
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.signOut();
    } catch {
      /* A failed sign-out still leaves this screen. */
    }
    setAthlete(null);
    setStatus("out");
  }, []);

  useEffect(() => {
    // The cookie lives on the API host, so the session is read in the browser.
    // A free Render wake can outlast one attempt. Retry once before staying on the wake screen.
    let live = true;
    let timer = 0;
    let tries = 0;
    const run = () => {
      void refreshSession().then((next) => {
        if (!live) return;
        if (next.status === "unreachable" && tries < 1) {
          tries += 1;
          setAthlete(null);
          setStatus("unreachable");
          timer = window.setTimeout(run, 2000);
          return;
        }
        setAthlete(next.athlete);
        setStatus(next.status);
      });
    };
    run();
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, []);

  const value = useMemo(() => ({ status, athlete, refresh, signOut }), [status, athlete, refresh, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("AuthProvider is missing");
  }
  return value;
}
