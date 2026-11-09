"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function EasyPace() {
  return (
    <RequireUser>
      <EasyPaceForm />
    </RequireUser>
  );
}

function EasyPaceForm() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [pace, setPace] = useState("");
  const [unit, setUnit] = useState<"mi" | "km">("mi");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!/^\d{1,2}:\d{2}$/.test(pace.trim())) {
      setError("Enter a pace like 7:25.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.patchSettings({ easy_pace: pace.trim(), easy_pace_unit: unit });
      await refresh();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Easy pace could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-plain">
      <Nav active="Home" />
      <main>
        <section className="rio-easy">
          <p className="rio-easy-kicker">Start here</p>
          <h1>Your easy pace</h1>
          <p>
            Easy and long runs use this pace. Enter minutes and seconds, like 7:25, and choose per mile or per
            kilometer. Quality workouts stay on your 800.
          </p>
        </section>
        {error ? <p className="rio-error">{error}</p> : null}
        <form className="rio-easy-form" onSubmit={onSubmit} noValidate>
          <label htmlFor="easy-pace">Easy pace</label>
          <input id="easy-pace" placeholder="7:25" value={pace} onChange={(event) => setPace(event.target.value)} />
          <p className="rio-easy-hint">Minutes and seconds, like 7:25.</p>
          <fieldset>
            <legend>Unit</legend>
            <label>
              <input type="radio" name="unit" checked={unit === "mi"} onChange={() => setUnit("mi")} /> per mile
            </label>
            <label>
              <input type="radio" name="unit" checked={unit === "km"} onChange={() => setUnit("km")} /> per kilometer
            </label>
          </fieldset>
          <button className="rio-primary" type="submit" disabled={busy}>
            Save easy pace
          </button>
        </form>
        <Footer />
      </main>
    </div>
  );
}
