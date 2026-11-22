import type { Metadata } from "next";
import { LastSessionView } from "@/components/LastSessionView";

export const metadata: Metadata = { title: "Last session · RIO" };

export default function Page() {
  return <LastSessionView />;
}
