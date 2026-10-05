import React, { useState } from 'react';
import type { Diagram, DiagramNode, DiagramEdge } from '../diagrams';
import type { Verdict } from '../evidence';
import { EvidenceBadge } from './EvidenceBadge';
import { DiagramInspectionDrawer } from './DiagramInspectionDrawer';
import { ArrowRight, Code, Eye } from 'lucide-react';

interface InteractiveDiagramProps {
  diagram: Diagram;
  onNavigateTab?: (tab: string, query?: string) => void;
  onInspectComponent?: (componentName: string) => void;
}

export const InteractiveDiagram: React.FC<InteractiveDiagramProps> = ({
  diagram,
  onNavigateTab,
  onInspectComponent,
}) => {
  const [selectedNode, setSelectedNode] = useState<DiagramNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<DiagramEdge | null>(null);
  const [viewTab, setViewTab] = useState<'interactive' | 'mermaid'>('interactive');
  const [filterKind, setFilterKind] = useState<string>('ALL');

  const nodes = diagram.nodes || [];
  const edges = diagram.edges || [];

  // Group nodes by kind
  const kinds = Array.from(new Set(nodes.map((n) => n.kind))).filter(Boolean);
  const filteredNodes = filterKind === 'ALL' ? nodes : nodes.filter((n) => n.kind === filterKind);

  const getKindColor = (kind: string) => {
    switch (kind.toLowerCase()) {
      case 'controller':
      case 'endpoint':
        return 'border-sky-500/40 bg-sky-500/10 text-sky-300 hover:border-sky-400';
      case 'service':
        return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:border-emerald-400';
      case 'repository':
      case 'dao':
        return 'border-purple-500/40 bg-purple-500/10 text-purple-300 hover:border-purple-400';
      case 'entity':
      case 'model':
        return 'border-amber-500/40 bg-amber-500/10 text-amber-300 hover:border-amber-400';
      default:
        return 'border-slate-700 bg-slate-800/60 text-slate-300 hover:border-slate-500';
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0B0F19] overflow-hidden space-y-4 p-5 shadow-2xl">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase">
              {diagram.type}
            </span>
            <EvidenceBadge verdict={(diagram.verdict || 'VERIFIED') as Verdict} compact />
          </div>
          <h3 className="text-base font-bold text-white font-mono tracking-tight">{diagram.title}</h3>
          {diagram.description && (
            <p className="text-xs text-slate-400 mt-0.5">{diagram.description}</p>
          )}
        </div>

        {/* View Switcher: Interactive Cards vs Mermaid */}
        <div className="flex items-center space-x-1 bg-[#101827] border border-slate-800 rounded-xl p-1 font-mono text-xs">
          <button
            onClick={() => setViewTab('interactive')}
            className={`px-3 py-1 rounded-lg flex items-center gap-1.5 transition-all ${
              viewTab === 'interactive'
                ? 'bg-indigo-600 text-white font-bold shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Interactive ({nodes.length})</span>
          </button>
          <button
            onClick={() => setViewTab('mermaid')}
            className={`px-3 py-1 rounded-lg flex items-center gap-1.5 transition-all ${
              viewTab === 'mermaid'
                ? 'bg-indigo-600 text-white font-bold shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            <span>Mermaid Spec</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {viewTab === 'interactive' ? (
        <div className="space-y-4">
          {/* Filter Pills */}
          {kinds.length > 1 && (
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
              <span className="text-slate-500 text-[10px] uppercase font-bold mr-1">Filter by:</span>
              <button
                onClick={() => setFilterKind('ALL')}
                className={`px-2 py-0.5 rounded-lg border transition-all ${
                  filterKind === 'ALL'
                    ? 'bg-slate-700 text-white border-slate-500 font-bold'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                All ({nodes.length})
              </button>
              {kinds.map((k) => (
                <button
                  key={k}
                  onClick={() => setFilterKind(k)}
                  className={`px-2 py-0.5 rounded-lg border transition-all ${
                    filterKind === k
                      ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500 font-bold'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {k} ({nodes.filter((n) => n.kind === k).length})
                </button>
              ))}
            </div>
          )}

          {/* Interactive Node Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto pr-1">
            {filteredNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              const outgoing = edges.filter((e) => e.source === node.id);

              return (
                <button
                  key={node.id}
                  onClick={() => {
                    setSelectedEdge(null);
                    setSelectedNode(isSelected ? null : node);
                    onInspectComponent?.(node.label || node.id);
                  }}
                  className={`text-left p-3 rounded-xl border transition-all font-mono space-y-2 relative group ${getKindColor(
                    node.kind,
                  )} ${isSelected ? 'ring-2 ring-indigo-400 shadow-lg' : ''}`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-bold text-xs truncate text-white">{node.label}</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-900/80 border border-slate-700 text-slate-300">
                      {node.kind}
                    </span>
                  </div>

                  {node.evidence_refs[0] && (
                    <div className="text-[10px] text-slate-400 truncate">
                      {node.evidence_refs[0].file_path}#L{node.evidence_refs[0].line_start}
                    </div>
                  )}

                  {outgoing.length > 0 && (
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
                      <ArrowRight className="w-3 h-3 text-emerald-400" />
                      <span>{outgoing.length} dependencies</span>
                    </div>
                  )}

                  <div className="text-[9px] text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity">
                    Click to inspect evidence & callers →
                  </div>
                </button>
              );
            })}
          </div>

          {/* Relationships Bar */}
          {edges.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-slate-800">
              <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Statically Verified Edges ({edges.length})
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto font-mono text-[10px]">
                {edges.slice(0, 20).map((edge, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setSelectedNode(null);
                      setSelectedEdge(edge);
                    }}
                    className={`px-2 py-1 rounded-lg border bg-[#111827] hover:border-sky-500 hover:text-white transition-all flex items-center gap-1 ${
                      selectedEdge === edge ? 'border-sky-400 text-sky-200' : 'border-slate-800 text-slate-400'
                    }`}
                  >
                    <span className="font-bold text-slate-200">{edge.source}</span>
                    <span className="text-slate-500">--[{edge.relationship.toLowerCase()}]--&gt;</span>
                    <span className="font-bold text-slate-200">{edge.target}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Mermaid Code Viewer */
        <div className="p-4 bg-[#070B14] rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto max-h-[360px] whitespace-pre leading-relaxed">
          {diagram.mermaid_source || 'No Mermaid source representation available.'}
        </div>
      )}

      {/* Drawer / Inspector Modal on Node / Edge Selection */}
      <DiagramInspectionDrawer
        selectedNode={selectedNode}
        selectedEdge={selectedEdge}
        allEdges={edges}
        onClose={() => {
          setSelectedNode(null);
          setSelectedEdge(null);
        }}
        onNavigateTab={onNavigateTab}
      />
    </div>
  );
};
