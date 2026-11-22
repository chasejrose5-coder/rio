import type { Metadata } from "next";
import { IntroGuide } from "@/components/IntroGuide";

export const metadata: Metadata = { title: "Intro · RIO" };

export default function Page() {
  return <IntroGuide />;
}
