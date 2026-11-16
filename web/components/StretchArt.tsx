import { POSES } from "@/lib/stretch-poses";

function line(from: readonly [number, number], to: readonly [number, number]): string {
  return `M${from[0]} ${from[1]} L${to[0]} ${to[1]}`;
}

/** A small original line drawing of one stretch. */
export function ExerciseArt({ id, title }: { id: number; title: string }) {
  const pose = POSES[id];
  if (!pose) return null;
  const d = [
    line(pose.shoulder, pose.hip),
    line(pose.shoulder, pose.lHand),
    line(pose.shoulder, pose.rHand),
    line(pose.hip, pose.lKnee),
    line(pose.lKnee, pose.lFoot),
    line(pose.hip, pose.rKnee),
    line(pose.rKnee, pose.rFoot),
    line(pose.head, pose.shoulder),
    ...pose.marks,
  ].join(" ");
  return (
    <svg className="rio-stretch-art" viewBox="0 0 200 150" role="img" aria-label={title}>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pose.head[0]} cy={pose.head[1]} r="8" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
