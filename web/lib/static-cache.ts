/** Cache-Control for files copied from ui/static.

Fonts are named by family, subset, and weight (see REQUIRED_FONT_FILES).
A new cut is a new filename, so a year of immutable cache is safe.
Photos keep a stable name such as login.jpg, so a replaced file must not
stick for a year. A day of freshness plus a week of stale-while-revalidate
is the long cache that is safe without a content hash.
*/

export const FONT_CACHE_CONTROL = "public, max-age=31536000, immutable";
export const PHOTO_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800";

export function staticAssetHeaders(): { source: string; headers: { key: string; value: string }[] }[] {
  return [
    { source: "/fonts/:path*", headers: [{ key: "Cache-Control", value: FONT_CACHE_CONTROL }] },
    { source: "/photos/:path*", headers: [{ key: "Cache-Control", value: PHOTO_CACHE_CONTROL }] },
  ];
}
