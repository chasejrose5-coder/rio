"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { prescribe, type StretchSession } from "@/lib/stretch";

/** A small link to today's stretches. The date is the one the page already loaded. */
export function StretchLink({ today, session }: { today: string; session?: StretchSession | null }) {
  const [fetched, setFetched] = useState<StretchSession | null | undefined>(undefined);

  useEffect(() => {
    if (session !== undefined || !today) return;
    let live = true;
    api
      .currentSeason()
      .then((season) => {
        if (!live) return;
        const sessions = season?.plan?.sessions;
        const match = Array.isArray(sessions) ? sessions.find((row) => row.date === today) : undefined;
        setFetched(match ?? null);
      })
      .catch(() => {
        if (!live) return;
        setFetched(null);
      });
    return () => {
      live = false;
    };
  }, [session, today]);

  const found = session !== undefined ? session : fetched;

  if (!today) return null;
  const names =
    found === undefined
      ? ""
      : prescribe({ today, session: found ?? null })
          .routines.map((item) => item.routine.name)
          .join(" · ");

  return (
    <p className="rio-stretch-link">
      <Link href="/stretch">Today&apos;s stretches</Link>
      {names ? <span>{names}</span> : null}
    </p>
  );
}
