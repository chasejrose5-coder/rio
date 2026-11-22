"use client";

import { useState, type FormEvent } from "react";
import { ApiError, api, previewing } from "@/lib/api";
import type { BikeOffer } from "@/lib/types";
import { ErrorText } from "./ErrorText";

const METERS = { miles: 1609.344, km: 1000 } as const;

function whole(text: string): number | null {
  if (!/^\d+$/.test(text.trim())) return null;
  return Number(text.trim());
}

function fromMeters(meters: number | null, units: string): string {
  if (meters == null || meters <= 0) return "";
  const scale = units === "km" ? METERS.km : METERS.miles;
  return (meters / scale).toFixed(1);
}

export function BikeCard({
  offer,
  units,
  onOffer,
}: {
  offer: BikeOffer;
  units: string;
  onOffer: (offer: BikeOffer) => void;
}) {
  const [minutes, setMinutes] = useState(offer.log?.minutes ? String(offer.log.minutes) : offer.minutes ? String(offer.minutes) : "");
  const [distance, setDistance] = useState(fromMeters(offer.log?.distance_m ?? null, units));
  const [heart, setHeart] = useState(offer.log?.avg_hr ? String(offer.log.avg_hr) : "");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const unitLabel = units === "km" ? "km" : "mi";
  const zone = offer.zone2;
  const logged = offer.log?.minutes || offer.log?.strava_id;

  async function send(body: { swap?: boolean; minutes?: number; distance_m?: number | null; avg_hr?: number | null }) {
    if (busy || previewing()) return;
    setBusy(true);
    setProblem("");
    try {
      onOffer(await api.bikeSave({ date: offer.date, ...body }));
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "That ride could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  function save(event: FormEvent) {
    event.preventDefault();
    const loggedMinutes = whole(minutes);
    if (loggedMinutes == null || loggedMinutes <= 0) {
      setProblem("Enter the ride in minutes.");
      return;
    }
    const body: { minutes: number; distance_m?: number | null; avg_hr?: number | null } = { minutes: loggedMinutes };
    if (distance.trim()) {
      const value = Number(distance);
      if (!Number.isFinite(value) || value < 0) {
        setProblem("Enter the ride distance.");
        return;
      }
      const scale = units === "km" ? METERS.km : METERS.miles;
      body.distance_m = Math.round(value * scale);
    } else {
      body.distance_m = null;
    }
    if (heart.trim()) {
      const bpm = whole(heart);
      if (bpm == null) {
        setProblem("Enter an average heart rate between 30 and 230.");
        return;
      }
      body.avg_hr = bpm;
    } else {
      body.avg_hr = null;
    }
    void send(body);
  }

  return (
    <section className="rio-bike-block" aria-label="Bike instead">
      <p className="rio-mark-label">Bike instead</p>
      {offer.minutes ? <p className="rio-note">{offer.minutes} min</p> : null}
      {zone ? (
        <p className="rio-note">
          Zone 2, {zone.low_bpm}-{zone.high_bpm} bpm. {zone.sentence}
        </p>
      ) : (
        <p className="rio-note">Easy bike is zone 2, conversational.</p>
      )}
      <p className="rio-note">Used {offer.swaps_used} of 2 this week.</p>
      {offer.suggest_first ? (
        <p className="rio-note">Suggested while a shin, Achilles, or foot area is rebuilding.</p>
      ) : null}
      {logged && offer.log?.strava_id ? <p className="rio-note">This ride came in from Strava.</p> : null}
      {offer.swapped ? (
        <form onSubmit={save}>
          <label htmlFor={`bike-minutes-${offer.date}`}>Minutes</label>
          <input
            id={`bike-minutes-${offer.date}`}
            inputMode="numeric"
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
          />
          <label htmlFor={`bike-distance-${offer.date}`}>Distance ({unitLabel})</label>
          <input
            id={`bike-distance-${offer.date}`}
            inputMode="decimal"
            value={distance}
            onChange={(event) => setDistance(event.target.value)}
          />
          <label htmlFor={`bike-hr-${offer.date}`}>Avg HR</label>
          <input
            id={`bike-hr-${offer.date}`}
            inputMode="numeric"
            value={heart}
            onChange={(event) => setHeart(event.target.value)}
          />
          <button className="rio-primary" type="submit" disabled={busy || previewing()}>
            Save ride
          </button>
          <button className="rio-secondary" type="button" disabled={busy || previewing()} onClick={() => void send({ swap: false })}>
            Run this easy day
          </button>
        </form>
      ) : (
        <button className="rio-primary" type="button" disabled={busy || previewing()} onClick={() => void send({ swap: true })}>
          Bike instead
        </button>
      )}
      {problem ? <ErrorText>{problem}</ErrorText> : null}
    </section>
  );
}
