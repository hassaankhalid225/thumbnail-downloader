import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "ThumbIQ has no accounts, no analytics cookies and no storage. Images live in a 60-minute memory cache and are then gone.",
};

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy"
      updated="27 July 2026"
      intro="ThumbIQ is built so there is very little to say here. There are no accounts, no signup, no advertising or analytics cookies, and nothing user-facing is ever written to disk."
      sections={[
        {
          heading: "What we collect",
          paragraphs: [
            "Nothing that identifies you. There is no account system, so there is no email address, no password and no profile.",
            "Your IP address is used transiently and in memory for rate limiting — so one visitor cannot exhaust the service for everyone else. It is not written to logs, not stored, and not shared.",
          ],
        },
        {
          heading: "What happens to the images",
          paragraphs: [
            "When you paste a link, ThumbIQ fetches the publicly served thumbnail, renders the download sizes, measures them, and streams the result back to you.",
            "Everything involved lives in a bounded in-memory cache and is evicted after at most 60 minutes. There is no object store, no database and no backup. A process restart clears everything immediately.",
          ],
          table: {
            headers: ["Data", "Where it lives", "How long"],
            rows: [
              ["Resolved thumbnail URLs", "In-memory TTL cache", "60 minutes"],
              ["Downloaded image bytes", "In-memory TTL cache", "60 minutes"],
              ["Generated download sizes", "In-memory TTL cache", "60 minutes"],
              ["Analysis results", "In-memory TTL cache, keyed by image content hash", "60 minutes"],
              ["Images you upload yourself", "Request memory only", "The life of the request"],
              ["Request logs", "Host, status and latency only — no full URLs, no IP addresses, no images", "14 days"],
            ],
          },
        },
        {
          heading: "EXIF and metadata",
          paragraphs: [
            "Every image is re-encoded before it reaches you, and EXIF is stripped in the process. If you upload your own draft, any camera metadata or GPS coordinates it carried are removed rather than passed along.",
          ],
        },
        {
          heading: "Faces",
          paragraphs: [
            "The analysis measures face geometry — position, size in frame, eye-line height — because those drive the composition score. It does not perform face recognition, identity matching or biometric templating, and it stores nothing about any face it detects.",
          ],
        },
        {
          heading: "Third parties",
          paragraphs: [
            "Two, and only when the relevant feature runs.",
          ],
          bullets: [
            "Platform CDNs (i.ytimg.com, vimeocdn.com and similar) receive a standard HTTP request for a public image. That is how the thumbnail is retrieved at all.",
            "Anthropic's Claude API receives the thumbnail, downscaled to a 1568-pixel long edge, plus the measurements taken from it, and returns the written verdict. It receives nothing about you. This step can be disabled entirely by the operator, and every other feature keeps working when it is.",
          ],
        },
        {
          heading: "Share links",
          paragraphs: [
            "A share link encodes the scores and palette directly into the URL. Nothing is stored on our side to make it work, which means a share link cannot expose anyone else's lookups and cannot outlive the person who created it.",
          ],
        },
        {
          heading: "Contact",
          paragraphs: [
            "Questions about any of this: privacy@thumbiq.app.",
          ],
        },
      ]}
    />
  );
}
