import { headers } from "next/headers";
import { LIVE_LABEL, LIVE_ORIGIN, isLegacyHost, requestHostname } from "@/lib/old-host";

/** A small note on an old host. The app under it keeps working. */
export async function OldHomeNote() {
  const incoming = await headers();
  const host = requestHostname(incoming.get("x-forwarded-host"), incoming.get("host"));
  if (!isLegacyHost(host)) return null;
  return (
    <p className="rio-old-home">
      RIO now lives at <a href={LIVE_ORIGIN}>{LIVE_LABEL}</a>.
    </p>
  );
}
