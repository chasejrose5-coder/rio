import type { Metadata } from "next";
import Script from "next/script";
import { Suspense, type ReactNode } from "react";
import { OldHomeNote } from "@/components/OldHomeNote";
import { AuthProvider } from "@/lib/auth";
import { LIVE_ORIGIN } from "@/lib/old-host";
import "./globals.css";

const description =
  "RIO builds an 800 meter plan from the times you enter and the runs you log. Your race, your plan, your result.";

/** Same-origin `/api` only. A laptop talks to localhost and does not ping Render. */
function wakeTarget(): string | null {
  const raw = (process.env.NEXT_PUBLIC_RIO_API_URL || "").trim().replace(/\/$/, "");
  if (!raw.startsWith("/")) return null;
  return `${raw}/health`;
}

export const metadata: Metadata = {
  metadataBase: new URL(LIVE_ORIGIN),
  title: "RIO · Runner Intelligence Owned",
  description,
  openGraph: {
    title: "RIO · Runner Intelligence Owned",
    description,
    url: LIVE_ORIGIN,
    siteName: "RIO",
    type: "website",
    locale: "en_US",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "RIO · Runner Intelligence Owned" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "RIO · Runner Intelligence Owned",
    description,
    images: ["/og.png"],
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const wake = wakeTarget();
  return (
    <html lang="en">
      <head>
        <link rel="preload" href="/fonts/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/inter-latin-500-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/inter-latin-600-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/manrope-latin-700-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/manrope-latin-800-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      </head>
      <body>
        {wake ? (
          <Script id="rio-wake" strategy="beforeInteractive">
            {`fetch(${JSON.stringify(wake)},{cache:"no-store",credentials:"omit",signal:AbortSignal.timeout(8000)}).then(function(r){return r.text()}).catch(function(){})`}
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
