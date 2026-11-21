import type { Prescription } from "@/lib/types";

/** Pace range and the safety line under a heart-rate workout. */
export function HeartPace({ heart, compact = false }: { heart?: Prescription["heart"]; compact?: boolean }) {
  if (!heart) return null;
  return (
    <div className="rio-hr-target">
      <p className="rio-pace-range">{heart.pace_line}</p>
      <p className="rio-hr-estimate">{heart.pace_note}</p>
      {compact ? null : (
        <>
          <p className="rio-settings-note">{heart.effort}</p>
          <p className="rio-hr-safety">{heart.safety}</p>
        </>
      )}
    </div>
  );
}
