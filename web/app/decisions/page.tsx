import type { Metadata } from "next";
import { DecisionsView } from "@/components/FixtureViews";

export const metadata: Metadata = { title: "Decisions · RIO" };

export default function Page() {
  return <DecisionsView />;
}
