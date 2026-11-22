import type { Metadata } from "next";
import { GoalView } from "@/components/FixtureViews";

export const metadata: Metadata = { title: "Goal · RIO" };

export default function Page() {
  return <GoalView />;
}