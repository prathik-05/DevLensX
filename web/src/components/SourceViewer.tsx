import React, { useEffect, useState } from 'react';
import { FileCode, ShieldAlert, RefreshCw } from 'lucide-react';
import type { ResolvedEvidence } from '../evidence';

interface SourceViewerProps {
  evidence: ResolvedEvidence;
  title?: string;
  onClose?: () => void;
}

/**
 * D5 SourceViewer — renders snapshot-resolved source lines with the cited
 * range highlighted. Renders explicit honest states for every failure mode
 * (stale commit, unknown snapshot, path violation, binary, too large).
 */
export const SourceViewer: React.FC<SourceViewerProps> = ({ evidence, title, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!evidence.resolved) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-4 space-y-2">
        <div className="flex items-center space-x-2 text-rose-300 font-mono text-xs font-bold uppercase">
          <ShieldAlert className="w-4 h-4" />
          <span>Evidence unavailable — {evidence.status}</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">{evidence.message}</p>
        <div className="font-mono text-[11px] text-slate-400 truncate">
          {evidence.ref.citation}
        </div>
      </div>
    );
  }

  const { ref, lines = [], total_lines = 0 } = evidence;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(
        lines.map((l) => `${String(l.n).padStart(4)} │ ${l.content}`).join('\n'),
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="rounded-xl border border-slate-700 bg-[#0B0F19] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 bg-[#111827] border-b border-slate-800">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-indigo-400 shrink-0" />
          <span className="text-xs font-mono font-bold text-white truncate">
            {title || ref.symbol_name || ref.file_path.split('/').pop()}
          </span>
          <span className="text-[10px] font-mono text-slate-400 truncate hidden sm:inline">
            {ref.file_path}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
            🟢 VERIFIED
          </span>
          <button
            onClick={handleCopy}
            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
          >
            {copied ? '✓ copied' : 'copy'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white text-sm leading-none px-1"
              aria-label="Close source viewer"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Code body */}
      <div className="overflow-x-auto max-h-[420px] overflow-y-auto font-mono text-[11px] leading-relaxed">
        {lines.map((line) => (
          <div
            key={line.n}
            className={`flex ${
              line.in_range
                ? 'bg-indigo-500/15 border-l-2 border-indigo-400'
                : 'border-l-2 border-transparent'
            }`}
          >
            <span className="select-none w-12 shrink-0 text-right pr-2 text-slate-500">
              {line.n}
            </span>
            <span
              className={`whitespace-pre flex-1 pr-3 ${
                line.in_range ? 'text-white' : 'text-slate-400'
              }`}
            >
              {line.content || ' '}
            </span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#111827] border-t border-slate-800 text-[10px] font-mono text-slate-500">
        <span>
          L{ref.line_start}-L{ref.line_end} of {total_lines}
        </span>
        {ref.commit_hash && <span>snapshot: {ref.commit_hash}</span>}
        {!ref.commit_hash && <RefreshCw className="w-3 h-3" />}
      </div>
    </div>
  );
};

/** Hook: fetch + hold resolved evidence for a citation click. */
export function useEvidenceResolver() {
  const [evidence, setEvidence] = useState<ResolvedEvidence | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => () => setEvidence(null), []);

  return { evidence, loading, setEvidence, setLoading };
}