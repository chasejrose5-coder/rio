"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STEPS = [
  ["Set your goal", "On Start, enter your 800 m times and choose Generate season plan."],
  ["Connect Strava", "In Settings, connect Strava so your runs show up."],
  ["Check your plan", "Open Plan each day and mark how it went."],
] as const;

export function IntroGuide() {
  return (
    <RequireUser>
      <IntroBody />
    </RequireUser>
  );
}

function IntroBody() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [error, setError] = useState("");

  async function finish() {
    try {
      await api.patchSettings({ intro_seen: true });
      await refresh();
      router.replace("/");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "The intro guide could not be saved. It will show again next time.",
      );
    }
  }

  return (
    <div className="page-plain">
      <Nav active="Home" />
      <main>
        <section className="rio-intro">
          <p className="rio-intro-kicker">Welcome</p>
          <h1>Start here</h1>
          <ol>
            {STEPS.map(([title, body], index) => (
              <li key={title}>
                <span>{index + 1}</span>
                <div>
                  <p className="rio-intro-title">{title}</p>
                  <p>{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
        {error ? <p className="rio-error">{error}</p> : null}
        <div className="rio-intro-actions">
          <button type="button" className="rio-secondary" onClick={() => void finish()}>
            Skip
          </button>
          <button type="button" className="rio-primary" onClick={() => void finish()}>
            Done
          </button>
        </div>
        <Footer />
      </main>
    </div>
  );
}
