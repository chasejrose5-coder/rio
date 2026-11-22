import type { Metadata } from "next";
import { HeartRateStep } from "@/components/HeartRateForm";

export const metadata: Metadata = { title: "Heart rate · RIO" };

export default function Page() {
  return <HeartRateStep />;
}
