import type { Metadata } from "next";
import { HomeView } from "@/components/HomeView";

export const metadata: Metadata = { title: "Home · RIO" };

export default function Page() {
  return <HomeView />;
}
