import type { Metadata } from "next";
import { GoogleCallback } from "@/components/GoogleCallback";

export const metadata: Metadata = {
  title: "Signing in · RIO",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <GoogleCallback />;
}
