import type { Clause } from "../lib/types";

/** Find the quote in the clause, tolerating whitespace and curly-quote differences. */
function locate(text: string, quote: string): [number, number] | null {
  if (!quote) return null;
  const norm = (s: string) => s.replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
  const t = norm(text);
  const q = norm(quote).trim();
  const direct = t.indexOf(q);
  if (direct >= 0) return [direct, direct + q.length];
  const pattern = q
    .split(/\s+/)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("\\s+");
  const m = new RegExp(pattern, "i").exec(t);
  return m ? [m.index, m.index + m[0].length] : null;
}

/**
 * The contract clause as a lawyer would mark it up: the risky words struck through
 * in correction red, and the proposed wording written in below in pen blue.
 */
export function Redline({ clause, quote, proposal }: { clause: Clause | null; quote: string; proposal: string }) {
  if (!clause) {
    return (
      <div className="redline">
        <p className="missing">This contract has no clause covering this. Proposed addition:</p>
        {proposal && <ins>{proposal}</ins>}
      </div>
    );
  }
  const span = locate(clause.text, quote);
  return (
    <div className="redline">
      <p>
        {clause.section_number && <span className="section-no">{clause.section_number}</span>}
        {span ? (
          <>
            {clause.text.slice(0, span[0])}
            <del>{clause.text.slice(span[0], span[1])}</del>
            {clause.text.slice(span[1])}
          </>
        ) : (
          clause.text
        )}
      </p>
      {proposal && <ins>{proposal}</ins>}
    </div>
  );
}
