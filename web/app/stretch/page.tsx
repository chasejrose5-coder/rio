import type { Metadata } from "next";
import { StretchView } from "@/components/StretchView";

export const metadata: Metadata = { title: "Stretching · RIO" };

export default function Page() {
  return <StretchView />;
}
