"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ResetScreen } from "@/components/AuthScreen";

function ResetFromLink() {
  const params = useSearchParams();
  const token = params.get("token") || params.get("token_hash") || "";
  return <ResetScreen token={token} />;
}

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Loading</p>}>
      <ResetFromLink />
    </Suspense>
  );
}
