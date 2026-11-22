import type { Metadata } from "next";
import { EasyPace } from "@/components/EasyPace";

export const metadata: Metadata = { title: "Easy pace · RIO" };

export default function Page() {
  return <EasyPace />;
}
