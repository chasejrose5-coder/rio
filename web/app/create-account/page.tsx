import type { Metadata } from "next";
import { CreateAccountScreen } from "@/components/AuthScreen";

export const metadata: Metadata = { title: "Create account · RIO" };

export default function Page() {
  return <CreateAccountScreen />;
}
