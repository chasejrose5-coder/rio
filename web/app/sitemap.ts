import type { MetadataRoute } from "next";
import { LIVE_ORIGIN } from "@/lib/old-host";
import { PUBLIC_PATHS } from "@/lib/public-routes";

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({
    url: path === "/" ? `${LIVE_ORIGIN}/` : `${LIVE_ORIGIN}${path}`,
    changeFrequency: path === "/" ? "weekly" : "monthly",
    priority: path === "/" ? 1 : 0.5,
  }));
}
