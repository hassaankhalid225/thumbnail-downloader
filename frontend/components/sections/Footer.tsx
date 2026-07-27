import Link from "next/link";

import { ANALYSIS_ENABLED, COPYRIGHT_LINE } from "@/lib/constants";

const PLATFORM_PAGES = [
  { href: "/youtube-thumbnail-downloader", label: "YouTube" },
  { href: "/tiktok-thumbnail-downloader", label: "TikTok" },
  { href: "/instagram-thumbnail-downloader", label: "Instagram" },
  { href: "/vimeo-thumbnail-downloader", label: "Vimeo" },
  { href: "/twitter-thumbnail-downloader", label: "X (Twitter)" },
  { href: "/facebook-thumbnail-downloader", label: "Facebook" },
];

const TOOL_PAGES = ANALYSIS_ENABLED
  ? [
      { href: "/", label: "Downloader + analyzer" },
      { href: "/compare", label: "Compare thumbnails" },
      { href: "/channel", label: "Channel pattern report" },
    ]
  : [{ href: "/", label: "Thumbnail downloader" }];

const LEGAL_PAGES = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
  { href: "/dmca", label: "DMCA / takedown" },
];

export function Footer() {
  return (
    <footer className="border-t border-[#232330] bg-[#0A0A0D]">
      <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <p className="text-[17px] font-extrabold tracking-tight">
              Thumb<span className="text-[#C8FF3D]">IQ</span>
            </p>
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-[#8E8EA8]">
              {ANALYSIS_ENABLED
                ? "Download any video thumbnail in every size, then find out — with real measurements, not vibes — why it works."
                : "Download any video thumbnail in every size the platform actually stores. Real file sizes, honest labels, nothing invented."}
            </p>
            <p className="eyebrow mt-5">No signup · No storage · Free</p>
          </div>

          <FooterColumn title="Platforms" links={PLATFORM_PAGES} />
          <FooterColumn title="Tools" links={TOOL_PAGES} />
          <FooterColumn title="Legal" links={LEGAL_PAGES} />
        </div>

        <div className="mt-12 border-t border-[#232330] pt-6">
          <p className="max-w-3xl text-xs leading-relaxed text-[#8E8EA8]">{COPYRIGHT_LINE}</p>
          <p className="mt-3 text-xs text-[#8E8EA8]">
            ThumbIQ is not affiliated with YouTube, TikTok, Meta, X, Vimeo or any other
            platform. Thumbnails are never stored — they live in a 60-minute memory cache
            and are then gone.
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string }[];
}) {
  return (
    <div>
      <p className="eyebrow">{title}</p>
      <ul className="mt-3 space-y-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="text-sm text-[#8E8EA8] transition-colors hover:text-[#F2F2F7]"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
