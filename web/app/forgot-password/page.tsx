import type { Metadata } from "next";
import { ForgotScreen } from "@/components/AuthScreen";

export const metadata: Metadata = { title: "Forgot password · RIO" };

export default function Page() {
  return <ForgotScreen />;
}
