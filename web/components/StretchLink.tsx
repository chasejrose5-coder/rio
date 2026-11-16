"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { prescribe, type StretchSession } from "@/lib/stretch";

/** A small link to today's stretches. The date is the one the page already loaded. */
export function StretchLink({
  today,
  session,
  sessions,
}: {
  today: string;
  session?: StretchSession | null;
  sessions?: StretchSession[];
}) {
  const [fetched, setFetched] = useState<{ session: StretchSession | null; sessions: StretchSession[] } | undefined>(
    undefined,
  );

  useEffect(() => {
    if (session !== undefined || !today) return;
    let live = true;
    api
      .currentSeason()
      .then((season) => {
        if (!live) return;
        const list = Array.isArray(season?.plan?.sessions) ? season.plan.sessions : [];
        const match = list.find((row) => row.date === today);
        setFetched({ session: match ?? null, sessions: list });
      })
      .catch(() => {
        if (!live) return;
        setFetched({ session: null, sessions: [] });
      });
    return () => {
      live = false;
    };
  }, [session, today]);

  const known =
    session !== undefined ? { session: session ?? null, sessions: sessions ?? [] } : fetched;

  if (!today) return null;
  const names =
    known === undefined
      ? ""
      : prescribe({ today, session: known.session, sessions: known.sessions })
          .routines.map((item) => item.routine.name)
          .join(" · ");

  return (
    <p className="rio-stretch-link">
      <Link href="/stretch">Today&apos;s stretches</Link>
      {names ? <span>{names}</span> : null}
    </p>
  );
}
