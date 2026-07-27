import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center px-5 py-20 text-center sm:px-8">
      <p className="mono text-6xl font-black text-[#232330]">404</p>
      <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">
        Nothing here to measure
      </h1>
      <p className="mt-3 max-w-md text-[15px] leading-relaxed text-[#8E8EA8]">
        That page doesn&apos;t exist. The tool is on the home page — paste a link and it
        goes to work.
      </p>
      <Link
        href="/"
        className="mt-7 rounded-xl bg-[#C8FF3D] px-6 py-3 text-sm font-bold text-black transition-all hover:brightness-110"
      >
        Back to ThumbIQ
      </Link>
    </div>
  );
}
