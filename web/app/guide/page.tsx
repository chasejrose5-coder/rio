import type { Metadata } from "next";
import { GuideView } from "@/components/GuideView";

export const metadata: Metadata = { title: "Guide · RIO" };

export default function Page() {
  return <GuideView />;
}
