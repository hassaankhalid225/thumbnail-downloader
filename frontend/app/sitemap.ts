import type { MetadataRoute } from "next";

import { ANALYSIS_ENABLED, SITE_URL } from "@/lib/constants";
import { PLATFORM_PAGES } from "@/lib/platformPages";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  // Compare and Channel are omitted while the analyser is off — submitting a URL that
  // only serves a "switched off" notice is a way to earn a thin-content penalty.
  const core: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: now, changeFrequency: "weekly", priority: 1 },
    ...(ANALYSIS_ENABLED
      ? ([
          { url: `${SITE_URL}/compare`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
          { url: `${SITE_URL}/channel`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
        ] satisfies MetadataRoute.Sitemap)
      : []),
  ];

  const platforms: MetadataRoute.Sitemap = PLATFORM_PAGES.map((page) => ({
    url: `${SITE_URL}/${page.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.9,
  }));

  const legal: MetadataRoute.Sitemap = ["privacy", "terms", "dmca"].map((slug) => ({
    url: `${SITE_URL}/${slug}`,
    lastModified: now,
    changeFrequency: "yearly",
    priority: 0.3,
  }));

  return [...core, ...platforms, ...legal];
}
