import type { Metadata } from "next";
import { Suspense } from "react";
import { StravaCallback } from "@/components/StravaCallback";

export const metadata: Metadata = { title: "Strava · RIO" };

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Connecting Strava</p>}>
      <StravaCallback />
    </Suspense>
  );
}
