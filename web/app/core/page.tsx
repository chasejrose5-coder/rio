import type { Metadata } from "next";
import { CoreView } from "@/components/CoreView";

export const metadata: Metadata = { title: "Core · RIO" };

export default function Page() {
  return <CoreView />;
}
