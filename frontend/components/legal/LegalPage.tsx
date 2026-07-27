export interface LegalSection {
  heading: string;
  paragraphs?: string[];
  bullets?: string[];
  table?: { headers: string[]; rows: string[][] };
}

export function LegalPage({
  title,
  updated,
  intro,
  sections,
}: {
  title: string;
  updated: string;
  intro: string;
  sections: LegalSection[];
}) {
  return (
    <>
      <header>
        <p className="eyebrow">Legal</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mono mt-2 text-[12px] text-[#8E8EA8]">Last updated {updated}</p>
        <p className="mt-5 text-[15px] leading-relaxed text-[#8E8EA8]">{intro}</p>
      </header>

      {sections.map((section) => (
        <section key={section.heading} className="space-y-3">
          <h2 className="pt-4 text-xl font-bold tracking-tight text-[#F2F2F7]">
            {section.heading}
          </h2>

          {section.paragraphs?.map((paragraph, index) => (
            <p key={index} className="text-[15px] leading-relaxed text-[#8E8EA8]">
              {paragraph}
            </p>
          ))}

          {section.bullets && (
            <ul className="space-y-2">
              {section.bullets.map((bullet, index) => (
                <li key={index} className="flex gap-2.5 text-[15px] leading-relaxed text-[#8E8EA8]">
                  <span className="text-[#C8FF3D]">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          )}

          {section.table && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] text-sm">
                <thead>
                  <tr className="border-b border-[#232330]">
                    {section.table.headers.map((header) => (
                      <th
                        key={header}
                        scope="col"
                        className="py-2.5 pr-4 text-left text-[12px] font-bold text-[#8E8EA8]"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {section.table.rows.map((row, index) => (
                    <tr key={index} className="border-b border-[#232330] last:border-0">
                      {row.map((cell, cellIndex) => (
                        <td
                          key={cellIndex}
                          className="py-3 pr-4 text-[13.5px] leading-relaxed text-[#8E8EA8]"
                        >
                          {cellIndex === 0 ? (
                            <span className="font-semibold text-[#F2F2F7]">{cell}</span>
                          ) : (
                            cell
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}
    </>
  );
}
