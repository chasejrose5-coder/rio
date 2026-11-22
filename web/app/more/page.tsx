import type { Metadata } from "next";
import { MoreView } from "@/components/MoreView";

export const metadata: Metadata = { title: "More · RIO" };

export default function Page() {
  return <MoreView />;
}
