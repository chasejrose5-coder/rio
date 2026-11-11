"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, refreshSession } from "./api";
import type { Athlete } from "./types";

type Status = "loading" | "in" | "out";

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

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
