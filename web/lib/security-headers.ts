/** Response headers for HTML and static files.

The broad policy is report-only. Next inlines a small boot script, and a
preview can load the Vercel toolbar. Enforcing that policy would risk
Strava's redirect, the self-hosted fonts and photos, or the toolbar.
`frame-ancestors` is enforced on its own, with `X-Frame-Options` for
older browsers. Neither directive touches scripts, fonts, or images.

`Access-Control-Allow-Origin: *` is not set in this repo. FastAPI allows
one configured origin. Vercel's CDN adds `*` on prerendered HTML and on
files in `public/`. These headers replace that on every path except
`/api`, so the proxied API keeps its own allowlist.
*/

export const SITE_ORIGIN = "https://www.riorunning.com";

const REPORT_ONLY = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "script-src 'self' 'unsafe-inline' https://vercel.live https://accounts.google.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  "connect-src 'self' https://rio-api.onrender.com https://vercel.live https://accounts.google.com",
  "frame-src https://vercel.live https://accounts.google.com",
  "form-action 'self'",
].join("; ");

export const DOCUMENT_SECURITY_HEADERS: { key: string; value: string }[] = [
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Content-Security-Policy-Report-Only", value: REPORT_ONLY },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Access-Control-Allow-Origin", value: SITE_ORIGIN },
];

/** Pages and public files. `/api` is the FastAPI proxy and is left alone. */
export function documentSecurityRoutes(): { source: string; headers: { key: string; value: string }[] }[] {
  return [
    { source: "/", headers: DOCUMENT_SECURITY_HEADERS },
    { source: "/:path((?!api$).*)", headers: DOCUMENT_SECURITY_HEADERS },
  ];
}
