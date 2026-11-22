import type { Metadata } from "next";
import { ActivityView } from "@/components/ActivityView";

export const metadata: Metadata = { title: "Activity · RIO" };

export default function Page() {
  return <ActivityView />;
}
