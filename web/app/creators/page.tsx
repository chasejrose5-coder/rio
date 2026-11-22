import type { Metadata } from "next";
import { CreatorsView } from "@/components/CreatorsView";

export const metadata: Metadata = { title: "Creators · RIO" };

export default function Page() {
  return <CreatorsView />;
}
