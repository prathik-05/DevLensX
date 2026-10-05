import React from 'react';
import { resolveEvidence } from '../apiClient';
import type { EvidenceRef } from '../evidence';
import { useEvidenceResolver } from './SourceViewer';
import { SourceViewer } from './SourceViewer';

interface EvidenceCitationProps {
  ref: EvidenceRef;
  label?: string;
  compact?: boolean;
}

/**
 * D5 EvidenceCitation — a clickable citation chip.
 *
 * The chip is a real navigational object: clicking resolves the citation
 * through the FULL snapshot identity (repository_id + analysis_run_id +
 * commit_hash + path + range) and opens the SourceViewer at that range.
 */
export const EvidenceCitation: React.FC<EvidenceCitationProps> = ({ ref, label, compact }) => {
  const { evidence, setEvidence, loading, setLoading } = useEvidenceResolver();

  const citationText = `${ref.file_path}#L${ref.line_start}-L${ref.line_end ?? ref.line_start}`;

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const resolved = await resolveEvidence(ref);
      setEvidence(resolved);
    } finally {
      setLoading(false);
    }
  };

  return (
    <span className="inline-block align-top">
      <button
        onClick={handleClick}
        disabled={loading}
        title={`Open source: ${citationText}`}
        className={`group inline-flex items-center gap-1 rounded border font-mono transition-all ${
          compact ? 'text-[10px] px-1.5 py-0.5' : 'text-[11px] px-2 py-1'
        } bg-indigo-950/60 border-indigo-700/60 text-indigo-300 hover:border-indigo-400 hover:text-indigo-200 disabled:opacity-60`}
      >
        <span className="truncate max-w-[280px]">{label || citationText}</span>
        {loading && <span className="animate-pulse">…</span>}
      </button>

      {(evidence || loading) && (
        <div className="mt-2">
          {loading ? (
            <div className="rounded-xl border border-slate-700 bg-[#0B0F19] px-3 py-2 text-[11px] font-mono text-slate-400 animate-pulse w-[320px]">
              Resolving evidence against snapshot…
            </div>
          ) : (
            evidence && (
              <SourceViewer
                evidence={evidence}
                onClose={() => setEvidence(null)}
              />
            )
          )}
        </div>
      )}
    </span>
  );
};