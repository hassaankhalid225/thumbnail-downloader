import type { Metadata } from "next";

import { SITE_URL } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Channel Thumbnail Pattern Report — Audit 24 Thumbnails at Once",
  description:
    "Paste a channel URL and see what it does repeatedly: the recurring palette, where the text always sits, how often a face appears, average word count, and a consistency score across the last 24 thumbnails.",
  alternates: { canonical: `${SITE_URL}/channel` },
  openGraph: {
    title: "Channel thumbnail pattern report | ThumbIQ",
    description:
      "The recurring palette, text-placement heatmap, face-usage rate and consistency score across a channel's last 24 thumbnails.",
    url: `${SITE_URL}/channel`,
  },
};

export default function ChannelLayout({ children }: { children: React.ReactNode }) {
  return children;
}
