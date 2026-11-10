"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import type { StravaStatus } from "@/lib/types";

export function StravaSettings() {
  return (
    <RequireUser>
      <StravaBody />
    </RequireUser>
  );
}

function StravaBody() {
  const params = useSearchParams();
  const flag = params.get("strava") || "";
  const [status, setStatus] = useState<StravaStatus | null>(null);
  const [problem, setProblem] = useState(flag === "error" ? "Strava could not be connected." : "");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setStatus(await api.stravaStatus());
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "Strava could not be reached.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  async function disconnect() {
    setBusy(true);
    setProblem("");
    try {
      await api.stravaDisconnect();
      await load();
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "Strava could not be disconnected.");
    } finally {
      setBusy(false);
    }
  }

  async function connect() {
    setBusy(true);
    setProblem("");
    try {
      const body = await api.stravaConnect();
      if (body.url) {
        window.location.assign(body.url);
        return;
      }
      setProblem("Strava could not be connected.");
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "Strava could not be connected.");
    } finally {
      setBusy(false);
    }
  }

  const name = status?.athlete_name?.trim() || "Strava athlete";

  return (
    <div className="page-settings">
      <Nav />
      <main>
        <header className="rio-hero">
          <h1>Settings</h1>
        </header>
        <section className="rio-card rio-strava-block">
          <p className="rio-mark-label">Strava</p>
          {status && !status.configured ? <p className="rio-note">Strava is not set up on this server yet.</p> : null}
          {status?.configured ? (
            <>
              <p className="rio-note">Strava data is only visible to you.</p>
              {status.connected ? (
                <>
                  <p className="rio-settings-note">Connected as {name}.</p>
                  <button type="button" className="rio-secondary" disabled={busy} onClick={() => void disconnect()}>
                    Disconnect
                  </button>
                </>
              ) : (
                <button type="button" className="rio-primary rio-strava-connect" disabled={busy} onClick={() => void connect()}>
                  Connect with Strava
                </button>
              )}
            </>
          ) : null}
          {problem ? <p className="rio-error">{problem}</p> : null}
          {flag === "connected" && status?.connected ? null : null}
        </section>
        <p className="rio-coming">Coming in the next step.</p>
        <Footer />
      </main>
    </div>
  );
}
