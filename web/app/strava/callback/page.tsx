import { Suspense } from "react";
import { StravaCallback } from "@/components/StravaCallback";

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Connecting Strava</p>}>
      <StravaCallback />
    </Suspense>
  );
}
