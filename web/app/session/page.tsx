import type { Metadata } from "next";
import { SessionView } from "@/components/SessionView";

export const metadata: Metadata = { title: "Session · RIO" };

export default function Page() {
  return <SessionView />;
}
