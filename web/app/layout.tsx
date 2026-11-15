import type { Metadata } from "next";
import Script from "next/script";
import { Suspense, type ReactNode } from "react";
import { OldHomeNote } from "@/components/OldHomeNote";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

/** Same-origin `/api` only. A laptop talks to localhost and does not ping Render. */
function wakeTarget(): string | null {
  const raw = (process.env.NEXT_PUBLIC_RIO_API_URL || "").trim().replace(/\/$/, "");
  if (!raw.startsWith("/")) return null;
  return `${raw}/health`;
}

export const metadata: Metadata = {
  title: "RIO · Runner Intelligence Owned",
  description: "Runner Intelligence Owned",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const wake = wakeTarget();
  return (
    <html lang="en">
      <head>
        <link rel="preload" href="/fonts/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/manrope-latin-700-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      </head>
      <body>
        {wake ? (
          <Script id="rio-wake" strategy="beforeInteractive">
            {`fetch(${JSON.stringify(wake)},{cache:"no-store",credentials:"omit"}).catch(function(){})`}
          </Script>
        ) : null}
        <Suspense fallback={null}>
          <OldHomeNote />
        </Suspense>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
