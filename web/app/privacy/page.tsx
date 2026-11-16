import type { Metadata } from "next";
import { LegalDocument } from "@/components/LegalDocument";
import { PRIVACY } from "@/lib/legal-copy";

export const metadata: Metadata = {
  title: "Privacy policy (draft) · RIO",
  description: PRIVACY.description,
};

export default function Page() {
  return <LegalDocument page={PRIVACY} />;
}
