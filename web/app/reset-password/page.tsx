import type { Metadata } from "next";
import ResetPasswordPage from "@/components/ResetPasswordPage";

export const metadata: Metadata = { title: "Reset password · RIO" };

export default function Page() {
  return <ResetPasswordPage />;
}
