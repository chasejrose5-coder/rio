"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { WorkSummary } from "@/lib/types";

type Row = { label: string; done: number };

async function one(work: () => Promise<WorkSummary>): Promise<Row | null> {
  try {
    const body = await work();
    if (!body || body.tracked !== true || typeof body.done !== "number" || !body.label) return null;
    return { label: body.label, done: body.done };
  } catch (caught) {
    if (caught instanceof ApiError) return null;
    return null;
  }
}

/** Done marks saved for injury prevention, core, and foam rolling this week. */
export function RecapMore({ start, end }: { start: string; end: string }) {
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    let live = true;
    void Promise.all([
      one(() => api.injurySummary(start, end)),
      one(() => api.coreSummary(start, end)),
      one(() => api.foamSummary(start, end)),
    ]).then((found) => {
      if (!live) return;
      setRows(found.filter((row): row is Row => row != null));
    });
    return () => {
      live = false;
    };
  }, [start, end]);

  if (!rows.length) return null;
  return (
    <>
      {rows.map((row) => (
        <div className="rio-field" key={row.label}>
          <dt>{row.label}</dt>
          <dd>{row.done === 1 ? "1 marked done" : `${row.done} marked done`}</dd>
        </div>
      ))}
    </>
  );
}
