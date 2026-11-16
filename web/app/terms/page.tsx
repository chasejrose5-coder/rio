import type { Metadata } from "next";
import { LegalDocument } from "@/components/LegalDocument";
import { TERMS } from "@/lib/legal-copy";

export const metadata: Metadata = {
  title: "Terms (draft) · RIO",
  description: TERMS.description,
};

export default function Page() {
  return <LegalDocument page={TERMS} />;
}
