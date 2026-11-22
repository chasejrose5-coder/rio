import type { Metadata } from "next";
import { LedgerView } from "@/components/FixtureViews";

export const metadata: Metadata = { title: "Ledger · RIO" };

export default function Page() {
  return <LedgerView />;
}
