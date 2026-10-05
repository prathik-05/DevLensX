import React from 'react';
import { Link2 } from 'lucide-react';
import type { EvidenceRef } from '../evidence';
import type { Verdict } from '../evidence';
import { EvidenceCitation } from './EvidenceCitation';
import { EvidenceBadge } from './EvidenceBadge';

interface EvidencePanelProps {
  title: string;
  citations: Array<EvidenceRef & { verdict?: Verdict; label?: string }>;
  relatedSymbols?: string[];
}

/**
 * D5 EvidencePanel — groups the evidence for one wiki page / answer / node:
 * clickable citations + optional verdict badges + related symbols.
 */
export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  title,
  citations,
  relatedSymbols,
}) => {
  if (!citations.length && !relatedSymbols?.length) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0B0F19] p-3 space-y-2.5">
      <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400">
        <Link2 className="w-3.5 h-3.5 text-indigo-400" />
        <span>{title}</span>
      </div>

      {citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {citations.map((c, i) => (
            <span key={`${c.file_path}-${c.line_start}-${i}`} className="inline-flex items-center gap-1">
              <EvidenceCitation ref={c} label={c.label} compact />
              {c.verdict && <EvidenceBadge verdict={c.verdict} compact />}
            </span>
          ))}
        </div>
      )}

      {!!relatedSymbols?.length && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-[10px] font-mono text-slate-500 mr-1">related:</span>
          {relatedSymbols.slice(0, 8).map((s) => (
            <span
              key={s}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-slate-300"
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};