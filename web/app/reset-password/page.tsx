"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ResetScreen } from "@/components/AuthScreen";
import { recoveryFromLocation, type RecoveryLink } from "@/lib/reset-link";

function ResetFromLink() {
  const params = useSearchParams();
  const [link, setLink] = useState<RecoveryLink | null>(null);

  useEffect(() => {
    // useSearchParams does not include the hash. Supabase puts the recovery
    // session there, so the fragment is read from the browser location.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLink(recoveryFromLocation(window.location.search, window.location.hash));
  }, [params]);

  if (!link) return <p className="rio-wait">Loading</p>;
  return <ResetScreen link={link} />;
}

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Loading</p>}>
      <ResetFromLink />
    </Suspense>
  );
}
