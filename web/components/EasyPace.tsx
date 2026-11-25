"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ErrorText } from "./ErrorText";
import {
  USUAL_LONG_HELP,
  USUAL_LONG_LABEL,
  distanceUnits,
  parseUsualLong,
  usualLongNote,
  usualLongPlaceholder,
  usualLongUnitLabel,
} from "@/lib/usual-long";

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
  const [usual, setUsual] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [kicker, setKicker] = useState("");

  useEffect(() => {
    let live = true;
    void api
      .currentSeason()
      .then((season) => {
        if (live) setKicker(season ? "Your paces" : "Start here");
      })
      .catch(() => {
        if (live) setKicker("Start here");
      });
    return () => {
      live = false;
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!/^\d{1,2}:\d{2}$/.test(pace.trim())) {
      setError("Enter a pace like 7:25.");
      return;
    }
    const units = distanceUnits(unit === "km" ? "km" : "miles");
    const parsed = parseUsualLong(usual, units);
    if (parsed && typeof parsed === "object") {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body: Record<string, unknown> = { easy_pace: pace.trim(), easy_pace_unit: unit };
      if (parsed != null) {
        body.usual_long_m = parsed;
        body.pace_units = unit;
      }
      await api.patchSettings(body);
      await refresh();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Easy pace could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const units = distanceUnits(unit === "km" ? "km" : "miles");
  const parsedUsual = parseUsualLong(usual, units);
  const clampNote = typeof parsedUsual === "number" ? usualLongNote(parsedUsual) : "";

  return (
    <div className="page-plain">
      <Nav />
      <main>
        <section className="rio-easy">
          <p className="rio-easy-kicker">{kicker}</p>
          <h1>Your easy pace</h1>
          <p>
            Easy and long runs use this pace. Enter minutes and seconds, like 7:25, and choose per mile or per
            kilometer. Quality workouts stay on your 800.
          </p>
        </section>
        {error ? <ErrorText>{error}</ErrorText> : null}
        <form className="rio-easy-form" onSubmit={onSubmit} noValidate>
          <label htmlFor="easy-pace">Easy pace</label>
          <input id="easy-pace" placeholder="7:25" value={pace} onChange={(event) => setPace(event.target.value)} />
          <p className="rio-easy-hint">Minutes and seconds, like 7:25.</p>
          <label htmlFor="usual-long">{USUAL_LONG_LABEL}</label>
          <input
            id="usual-long"
            inputMode="decimal"
            placeholder={usualLongPlaceholder(units)}
            value={usual}
            onChange={(event) => setUsual(event.target.value)}
          />
          <p className="rio-easy-hint">
            {USUAL_LONG_HELP} Optional. In {usualLongUnitLabel(units)}.
          </p>
          {clampNote ? <p className="rio-easy-hint">{clampNote}</p> : null}
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
        <Footer page="easy-pace" />
      </main>
    </div>
  );
}
