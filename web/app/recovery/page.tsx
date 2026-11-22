import type { Metadata } from "next";
import { RecoveryView } from "@/components/RecoveryView";

export const metadata: Metadata = { title: "Recovery · RIO" };

export default function Page() {
  return <RecoveryView />;
}
