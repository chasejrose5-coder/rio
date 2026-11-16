import assert from "node:assert/strict";
import test from "node:test";
import { FONT_CACHE_CONTROL, PHOTO_CACHE_CONTROL, staticAssetHeaders } from "./static-cache.ts";

test("fonts are immutable and photos are long-cached but replaceable", () => {
  const headers = staticAssetHeaders();
  const font = headers.find((item) => item.source.startsWith("/fonts"));
  const photo = headers.find((item) => item.source.startsWith("/photos"));
  assert.equal(font?.headers[0]?.value, FONT_CACHE_CONTROL);
  assert.match(FONT_CACHE_CONTROL, /immutable/);
  assert.equal(photo?.headers[0]?.value, PHOTO_CACHE_CONTROL);
  assert.equal(PHOTO_CACHE_CONTROL.includes("immutable"), false);
  assert.match(PHOTO_CACHE_CONTROL, /max-age=86400/);
  assert.match(PHOTO_CACHE_CONTROL, /stale-while-revalidate=604800/);
});
