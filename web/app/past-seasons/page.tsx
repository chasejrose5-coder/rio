import type { Metadata } from "next";
import { PastSeasonsView } from "@/components/PastSeasonsView";

export const metadata: Metadata = { title: "Past seasons · RIO" };

export default function Page() {
  return <PastSeasonsView />;
}
