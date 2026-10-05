import React from 'react';
import type { DiagramNode, DiagramEdge } from '../diagrams';
import type { Verdict } from '../evidence';
import { EvidenceCitation } from './EvidenceCitation';
import { EvidenceBadge } from './EvidenceBadge';
import { SourceViewer, useEvidenceResolver } from './SourceViewer';
import { resolveEvidence } from '../apiClient';
import { FileCode, ArrowRight, ShieldCheck, Zap, Layers, GitFork, X } from 'lucide-react';

interface DiagramInspectionDrawerProps {
  selectedNode: DiagramNode | null;
  selectedEdge: DiagramEdge | null;
  allEdges: DiagramEdge[];
  onClose: () => void;
  onNavigateTab?: (tab: string, query?: string) => void;
}

export const DiagramInspectionDrawer: React.FC<DiagramInspectionDrawerProps> = ({
  selectedNode,
  selectedEdge,
  allEdges,
  onClose,
  onNavigateTab,
}) => {
  const { evidence, setEvidence, loading, setLoading } = useEvidenceResolver();

  if (!selectedNode && !selectedEdge) return null;

  // If node is selected
  if (selectedNode) {
    const primaryRef = selectedNode.evidence_refs[0];
    const incomingEdges = allEdges.filter((e) => e.target === selectedNode.id);
    const outgoingEdges = allEdges.filter((e) => e.source === selectedNode.id);

    const handleOpenSource = async () => {
      if (!primaryRef || loading) return;
      setLoading(true);
      try {
        const resolved = await resolveEvidence(primaryRef);
        setEvidence(resolved);
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="rounded-2xl border border-slate-800 bg-[#0E1526] p-5 space-y-4 shadow-2xl animate-in fade-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white font-mono">{selectedNode.label}</h3>
              <span className="text-[10px] font-mono text-slate-400">{selectedNode.kind}</span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <EvidenceBadge verdict={(selectedNode.verdict || 'VERIFIED') as Verdict} compact />
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
              aria-label="Close inspection drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Evidence Citations */}
        {selectedNode.evidence_refs.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Verified Line Provenance
            </div>
            <div className="flex flex-wrap gap-1.5">
              {selectedNode.evidence_refs.map((ref, idx) => (
                <EvidenceCitation key={`${ref.file_path}-${ref.line_start}-${idx}`} ref={ref} compact />
              ))}
            </div>
          </div>
        )}

        {/* Relationships (Incoming / Outgoing) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
          <div className="p-3 bg-[#070B14] border border-slate-800 rounded-xl space-y-1">
            <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1">
              <GitFork className="w-3 h-3 text-sky-400" />
              Incoming Callers ({incomingEdges.length})
            </span>
            <div className="flex flex-wrap gap-1">
              {incomingEdges.length > 0 ? (
                incomingEdges.map((e, idx) => (
                  <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                    {e.source}
                  </span>
                ))
              ) : (
                <span className="text-[10px] text-slate-500">Root Entrypoint</span>
              )}
            </div>
          </div>

          <div className="p-3 bg-[#070B14] border border-slate-800 rounded-xl space-y-1">
            <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1">
              <ArrowRight className="w-3 h-3 text-emerald-400" />
              Dependencies ({outgoingEdges.length})
            </span>
            <div className="flex flex-wrap gap-1">
              {outgoingEdges.length > 0 ? (
                outgoingEdges.map((e, idx) => (
                  <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                    {e.target}
                  </span>
                ))
              ) : (
                <span className="text-[10px] text-slate-500">Leaf Component</span>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons: [Open Source], [Explain], [Show Impact] */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800">
          {primaryRef && (
            <button
              onClick={handleOpenSource}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>{loading ? 'Resolving…' : 'Open Source'}</span>
            </button>
          )}

          {onNavigateTab && (
            <>
              <button
                onClick={() =>
                  onNavigateTab('copilot', `Explain the architectural responsibilities and implementation details of component ${selectedNode.label}.`)
                }
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all border border-slate-700"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Explain in Copilot</span>
              </button>

              <button
                onClick={() =>
                  onNavigateTab('build', selectedNode.label)
                }
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all border border-slate-700"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Show Impact</span>
              </button>
            </>
          )}
        </div>

        {/* Inline Source Viewer if active */}
        {evidence && (
          <div className="pt-2">
            <SourceViewer evidence={evidence} onClose={() => setEvidence(null)} />
          </div>
        )}
      </div>
    );
  }

  // If edge is selected
  if (selectedEdge) {
    const primaryRef = selectedEdge.evidence_refs[0];

    const handleOpenEdgeSource = async () => {
      if (!primaryRef || loading) return;
      setLoading(true);
      try {
        const resolved = await resolveEvidence(primaryRef);
        setEvidence(resolved);
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="rounded-2xl border border-slate-800 bg-[#0E1526] p-5 space-y-4 shadow-2xl animate-in fade-in duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <GitFork className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white font-mono">
                {selectedEdge.source} → {selectedEdge.target}
              </h3>
              <span className="text-[10px] font-mono text-slate-400">{selectedEdge.relationship}</span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <EvidenceBadge verdict={selectedEdge.verdict as Verdict} compact />
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
              aria-label="Close inspection drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {selectedEdge.evidence_refs.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Relationship Evidence Provenance
            </div>
            <div className="flex flex-wrap gap-1.5">
              {selectedEdge.evidence_refs.map((ref, idx) => (
                <EvidenceCitation key={`${ref.file_path}-${ref.line_start}-${idx}`} ref={ref} compact />
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
          {primaryRef && (
            <button
              onClick={handleOpenEdgeSource}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>{loading ? 'Resolving…' : 'Open Source'}</span>
            </button>
          )}
        </div>

        {evidence && (
          <div className="pt-2">
            <SourceViewer evidence={evidence} onClose={() => setEvidence(null)} />
          </div>
        )}
      </div>
    );
  }

  return null;
};
