import type { Metadata } from "next";
import { NextView } from "@/components/FixtureViews";

export const metadata: Metadata = { title: "Next · RIO" };

export default function Page() {
  return <NextView />;
}
