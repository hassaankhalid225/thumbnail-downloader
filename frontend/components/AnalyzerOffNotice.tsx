import Link from "next/link";

/**
 * Shown on the analyser-only routes while `NEXT_PUBLIC_ENABLE_ANALYSIS` is off.
 *
 * The routes stay reachable rather than 404ing: someone arriving from a bookmark or a
 * search result should learn what happened and where to go, not hit a dead end. They are
 * dropped from the nav and the sitemap so nothing new points at them in the meantime.
 */
export function AnalyzerOffNotice({ feature }: { feature: string }) {
  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center sm:px-8">
      <p className="eyebrow">Temporarily off</p>
      <h1 className="mt-3 text-2xl font-extrabold tracking-tight sm:text-3xl">
        {feature} is switched off right now
      </h1>
      <p className="mt-4 text-[15px] leading-relaxed text-[#8E8EA8]">
        The analyzer is paused while we finish it. The downloader is fully working — paste
        any video link and take the thumbnail in every size the platform actually stores.
      </p>
      <Link
        href="/"
        className="mt-7 inline-block rounded-xl bg-[#C8FF3D] px-6 py-3 text-sm font-bold text-black transition-all hover:brightness-110"
      >
        Go to the downloader
      </Link>
    </div>
  );
}
