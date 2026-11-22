import type { Metadata } from "next";
import { FoamView } from "@/components/FoamView";

export const metadata: Metadata = { title: "Foam rolling · RIO" };

export default function Page() {
  return <FoamView />;
}
