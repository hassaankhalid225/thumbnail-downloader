export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-5 py-16 sm:px-8">
      <article className="prose-thumbiq space-y-6">{children}</article>
    </div>
  );
}
