import type { Metadata } from "next";
import { StartForm } from "@/components/StartForm";

export const metadata: Metadata = { title: "Start · RIO" };

export default function Page() {
  return <StartForm />;
}
