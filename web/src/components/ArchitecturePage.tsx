import React, { useState, useEffect } from 'react';
import type { AnalysisResponse } from '../types';
import type { Diagram, DiagramType } from '../diagrams';
import { fetchDiagram, explainArchitecture } from '../apiClient';
import { InteractiveDiagram } from './InteractiveDiagram';
import { GalaxyConstellationGraph } from './GalaxyConstellationGraph';
import { ComponentInspectorDrawer } from './ComponentInspectorDrawer';
import {
  Layers,
  Database,
  Server,
  Terminal,
  Compass,
  Sparkles,
  Network,
  CheckCircle2,
  Cpu,
  Loader2,
  Search
} from 'lucide-react';

interface ArchitecturePageProps {
  data: AnalysisResponse;
  onNavigateTab?: (tab: string, query?: string) => void;
}

interface ArchitectureNarrative {
  repository: string;
  inferred_style: string;
  narrative: string;
  observed_layers: Array<{ layer: string; count: number; examples?: string[] }>;
  observed_flow: string[];
  total_classes: number;
  total_relationships: number;
  verdict: string;
  inference_label: string;
}

export const ArchitecturePage: React.FC<ArchitecturePageProps> = ({ data, onNavigateTab }) => {
  const [viewMode, setViewMode] = useState<'diagrams' | 'galaxy' | 'graph' | 'layered'>('diagrams');
  const [activeDiagramType, setActiveDiagramType] = useState<DiagramType>('ARCHITECTURE');
  const [activeDiagram, setActiveDiagram] = useState<Diagram | null>(null);
  const [diagramLoading, setDiagramLoading] = useState<boolean>(false);
  const [inspectedComponent, setInspectedComponent] = useState<string | null>(null);
  const [compFilter, setCompFilter] = useState<string>('');

  // AI Architecture Reasoning State
  const [archNarrative, setArchNarrative] = useState<ArchitectureNarrative | null>(null);
  const [loadingNarrative, setLoadingNarrative] = useState<boolean>(false);

  const keyComponents = React.useMemo(() => {
    const nodes = data?.knowledge_graph?.nodes || [];
    const list: any[] = nodes.length > 0 ? nodes : ((data as any)?.classes || []);
    return list
      .map((c: any) => ({ name: c.name || c.id, stereotype: c.stereotype || c.kind || 'Component' }))
      .filter((c: any) => c.name && !c.name.includes('$') && !c.name.includes('Test'))
      .slice(0, 20);
  }, [data]);

  useEffect(() => {
    let cancelled = false;
    async function loadCurrentDiagram() {
      if (!data.analysis_run_id) return;
      setDiagramLoading(true);
      try {
        const diag = await fetchDiagram(data.analysis_run_id, activeDiagramType);
        if (!cancelled && diag) {
          setActiveDiagram(diag);
        }
      } finally {
        if (!cancelled) setDiagramLoading(false);
      }
    }
    loadCurrentDiagram();
    return () => { cancelled = true; };
  }, [data.analysis_run_id, activeDiagramType]);

  useEffect(() => {
    let cancelled = false;
    async function loadArchExplanation() {
      setLoadingNarrative(true);
      try {
        const res = await explainArchitecture(data.analysis_run_id);
        if (!cancelled && res && res.status === 'success') {
          setArchNarrative(res);
        }
      } catch (err) {
        console.warn('explainArchitecture error:', err);
      } finally {
        if (!cancelled) setLoadingNarrative(false);
      }
    }
    loadArchExplanation();
    return () => { cancelled = true; };
  }, [data.analysis_run_id]);

  const layers = [
    { title: '1. Web / API Layer', desc: 'Request handlers & API endpoints', count: data.repo_summary?.controllers || 0, icon: Terminal, color: '#0284c7' },
    { title: '2. Business Logic Layer', desc: 'Core domain workflows & rules', count: data.repo_summary?.services || 0, icon: Server, color: '#059669' },
    { title: '3. Data Access Layer', desc: 'Database queries & persistence', count: data.repo_summary?.repositories || 0, icon: Database, color: '#7c3aed' },
    { title: '4. Domain Model Layer', desc: 'Data models & schema entities', count: data.repo_summary?.entities || 0, icon: Layers, color: '#d97706' }
  ];

  const diagramTypes: Array<{ type: DiagramType; label: string }> = [
    { type: 'ARCHITECTURE', label: 'Architecture Layers' },
    { type: 'DEPENDENCY', label: 'Dependencies' },
    { type: 'COMPONENT', label: 'Module Hierarchy' },
    { type: 'CALL_GRAPH', label: 'Call Graph' },
    { type: 'DATA_FLOW', label: 'Data Flow' },
    { type: 'SEQUENCE', label: 'Sequence Flow' },
  ];

  return (
    <div className="space-y-6 font-sans bg-white dark:bg-[#0a0a0f] text-black dark:text-[#f8fafc]">
      {/* Workspace Header */}
      <div className="border-b-2 border-black dark:border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-sky-100 text-sky-900 dark:bg-sky-950/60 dark:text-sky-300 border-2 border-black dark:border-sky-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              HYBRID GRAPHRAG ARCHITECTURE
            </span>
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-2 border-black dark:border-emerald-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              ● KÙZU EVIDENCE VERIFIED
            </span>
          </div>
          <h1 className="text-2xl font-black text-black dark:text-white flex items-center space-x-2 tracking-tight">
            <Compass className="w-6 h-6 text-[#0284c7]" />
            <span>Architecture Universe & Interactive Diagrams</span>
          </h1>
          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium mt-1">
            Statically verified AST diagrams with line-level evidence provenance across {data.repo_summary?.total_classes || 0} classes.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center space-x-1 p-1 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-700 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none font-sans text-xs">
          <button
            onClick={() => setViewMode('diagrams')}
            className={`px-3 py-1.5 flex items-center space-x-1.5 transition-all font-bold rounded-sm ${
              viewMode === 'diagrams'
                ? 'bg-black text-white dark:bg-sky-600 dark:text-white shadow-[2px_2px_0px_0px_#000000] dark:shadow-[0_0_12px_rgba(2,132,199,0.35)]'
                : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80'
            }`}
          >
            <Network className="w-4 h-4" />
            <span>Evidence Diagrams</span>
          </button>
          <button
            onClick={() => setViewMode('galaxy')}
            className={`px-3 py-1.5 flex items-center space-x-1.5 transition-all font-bold rounded-sm ${
              viewMode === 'galaxy'
                ? 'bg-black text-white dark:bg-sky-600 dark:text-white shadow-[2px_2px_0px_0px_#000000] dark:shadow-[0_0_12px_rgba(2,132,199,0.35)]'
                : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Galaxy Constellation</span>
          </button>

          <button
            onClick={() => setViewMode('layered')}
            className={`px-3 py-1.5 flex items-center space-x-1.5 transition-all font-bold rounded-sm ${
              viewMode === 'layered'
                ? 'bg-black text-white dark:bg-sky-600 dark:text-white shadow-[2px_2px_0px_0px_#000000] dark:shadow-[0_0_12px_rgba(2,132,199,0.35)]'
                : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Layer Flow View</span>
          </button>
        </div>
      </div>

      {/* Grounded AI Architectural Reasoning Card */}
      {loadingNarrative && (
        <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-4 text-xs font-mono text-slate-700 dark:text-slate-300 flex items-center space-x-2 shadow-[3px_3px_0px_0px_#000000]">
          <Loader2 className="w-4 h-4 animate-spin text-[#0284c7]" />
          <span className="font-bold">Synthesizing grounded architectural reasoning via Hybrid GraphRAG...</span>
        </div>
      )}
      {archNarrative && (
        <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-5 space-y-4 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
          <div className="flex flex-wrap items-center justify-between border-b-2 border-black dark:border-slate-800 pb-3 gap-2">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-[#0284c7]" />
              <span className="font-sans text-xs font-black text-black dark:text-white uppercase tracking-wider">
                Architectural Style & Pattern Reasoning
              </span>
            </div>
            <div className="flex items-center space-x-2 font-mono text-[10px]">
              <span className="px-2.5 py-1 bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border border-black dark:border-emerald-500 font-bold flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{archNarrative.verdict}</span>
              </span>
              <span className="px-2.5 py-1 bg-purple-100 text-purple-900 dark:bg-purple-950/60 dark:text-purple-300 border border-black dark:border-purple-500 font-bold">
                {archNarrative.inference_label}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-black text-black dark:text-white font-sans">
              Pattern: <span className="text-[#0284c7]">{archNarrative.inferred_style}</span>
            </div>
            <div className="text-xs text-slate-900 dark:text-slate-100 leading-relaxed font-sans whitespace-pre-line bg-slate-50 dark:bg-[#070b14] p-3.5 border-2 border-black/20 dark:border-slate-800 font-medium">
              {archNarrative.narrative}
            </div>
          </div>

          {/* Observed Flow Traces */}
          {archNarrative.observed_flow && archNarrative.observed_flow.length > 0 && (
            <div className="space-y-1 font-mono text-xs">
              <span className="text-[10px] text-slate-700 dark:text-slate-300 uppercase font-black block font-sans">
                Observed Layer Flow (Deterministic Kùzu Traversal):
              </span>
              <div className="flex flex-wrap gap-2">
                {archNarrative.observed_flow.map((flow, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 bg-slate-100 dark:bg-[#181824] border border-black dark:border-slate-700 text-black dark:text-white font-bold text-[11px] flex items-center space-x-1 shadow-[1px_1px_0px_0px_#000000]"
                  >
                    <span>{flow}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* D6 Interactive Evidence Diagram View */}
      {viewMode === 'diagrams' && (
        <div className="space-y-4">
          {/* Fast Component Inspector Selector Bar */}
          {keyComponents.length > 0 && (
            <div className="p-3 bg-slate-50 dark:bg-[#12131a] border-2 border-black dark:border-slate-800 space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none font-sans">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-black uppercase text-black dark:text-white flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-[#0284c7]" />
                  <span>Component Inspector — Click any component for live AST slide-over:</span>
                </span>
                <div className="flex items-center gap-1.5">
                  <Search className="w-3 h-3 text-slate-500" />
                  <input
                    type="text"
                    value={compFilter}
                    onChange={(e) => setCompFilter(e.target.value)}
                    placeholder="Filter components…"
                    className="px-2 py-0.5 text-[11px] font-mono border border-black dark:border-slate-700 bg-white dark:bg-[#0c0e14] text-black dark:text-white rounded-none outline-none"
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                {keyComponents
                  .filter((c) => !compFilter || c.name.toLowerCase().includes(compFilter.toLowerCase()))
                  .map((c) => (
                    <button
                      key={c.name}
                      onClick={() => setInspectedComponent(c.name)}
                      className="px-2.5 py-1 text-[11px] font-mono font-bold bg-white dark:bg-[#1a1c26] text-black dark:text-slate-200 border border-black dark:border-slate-700 hover:bg-sky-100 dark:hover:bg-sky-900/50 hover:border-sky-500 transition-all flex items-center gap-1 shadow-[1px_1px_0px_0px_#000000] dark:shadow-none"
                    >
                      <span>{c.name}</span>
                      <span className="text-[9px] text-slate-500 uppercase">[{c.stereotype}]</span>
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* Diagram Type Selector Bar */}
          <div className="flex flex-wrap items-center gap-2 p-2 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-700 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none font-sans text-xs">
            {diagramTypes.map((dt) => (
              <button
                key={dt.type}
                onClick={() => setActiveDiagramType(dt.type)}
                className={`px-3 py-1.5 transition-all font-bold rounded-sm ${
                  activeDiagramType === dt.type
                    ? 'bg-black text-white dark:bg-sky-600 dark:text-white shadow-[2px_2px_0px_0px_#000000] dark:shadow-[0_0_12px_rgba(2,132,199,0.35)]'
                    : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80'
                }`}
              >
                {dt.label}
              </button>
            ))}
          </div>

          {activeDiagram ? (
            <InteractiveDiagram
              diagram={activeDiagram}
              onNavigateTab={onNavigateTab}
              onInspectComponent={setInspectedComponent}
            />
          ) : (
            <div className="p-8 border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] text-center font-sans text-xs text-slate-600 dark:text-slate-400 font-bold shadow-[3px_3px_0px_0px_#000000]">
              {diagramLoading ? 'Generating evidence diagram…' : 'No diagram generated for this repository yet.'}
            </div>
          )}
        </div>
      )}

      {/* Main Galaxy Constellation Graph */}
      {viewMode === 'galaxy' && (
        <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-4 sm:p-6 space-y-4 shadow-[3px_3px_0px_0px_#000000]">
          <GalaxyConstellationGraph data={data} />
        </div>
      )}



      {/* Layer Flow View */}
      {viewMode === 'layered' && (
        <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-6 space-y-6 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
          <div className="flex flex-wrap items-center justify-between border-b-2 border-black dark:border-slate-800 pb-3 gap-2">
            <div>
              <h2 className="text-sm font-black text-black dark:text-white uppercase tracking-wider font-sans">
                Layer Flow & Component Relationship Map
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-sans mt-0.5">
                Displays real component dependencies across architectural layers. Click any component to open grounded AST source evidence.
              </p>
            </div>

            {/* Architecture Legend */}
            <div className="flex flex-wrap items-center gap-2 p-2 bg-slate-50 dark:bg-[#070b14] border border-black/20 dark:border-slate-800 font-mono text-[10px]">
              <span className="font-bold font-sans uppercase text-slate-500 mr-1">Legend:</span>
              <span className="flex items-center gap-1 text-[#0284c7] font-bold">
                <span className="w-2 h-2 rounded-full bg-[#0284c7]" /> Controller / API
              </span>
              <span className="flex items-center gap-1 text-[#059669] font-bold">
                <span className="w-2 h-2 rounded-full bg-[#059669]" /> Service
              </span>
              <span className="flex items-center gap-1 text-[#7c3aed] font-bold">
                <span className="w-2 h-2 rounded-full bg-[#7c3aed]" /> Repository
              </span>
              <span className="flex items-center gap-1 text-[#d97706] font-bold">
                <span className="w-2 h-2 rounded-full bg-[#d97706]" /> Entity / Model
              </span>
              <span className="flex items-center gap-1 text-slate-400 font-bold">
                ➔ INJECTS / CALLS
              </span>
            </div>
          </div>

          {/* Layer Cards Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {layers.map((layer, idx) => {
              const Icon = layer.icon;
              return (
                <div key={idx} className="bg-slate-50 dark:bg-[#070b14] p-4 border-2 border-black dark:border-slate-800 space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
                  <div className="flex items-center justify-between">
                    <div className="w-8 h-8 bg-white dark:bg-[#12131a] border border-black dark:border-slate-700 flex items-center justify-center">
                      <Icon className="w-4 h-4" style={{ color: layer.color }} />
                    </div>
                    <span className="text-xl font-black text-black dark:text-white font-mono">{layer.count}</span>
                  </div>
                  <div>
                    <div className="text-xs font-black text-black dark:text-white font-sans">{layer.title}</div>
                    <div className="text-[10px] text-slate-600 dark:text-slate-400 font-medium">{layer.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Genuine Component Flow Grid */}
          <div className="space-y-4">
            <h3 className="text-xs font-black text-black dark:text-white uppercase tracking-wider font-sans">
              Observed Component Traversal & Dependencies:
            </h3>

            {keyComponents.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-700">
                No component relationships indexed for this snapshot yet.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {keyComponents.map((c) => {
                  const rawComp = ((data as any)?.classes || []).find((rc: any) => rc.name === c.name);
                  const deps = rawComp?.injected_dependencies || [];
                  const methods = rawComp?.methods || [];

                  return (
                    <div
                      key={c.name}
                      onClick={() => setInspectedComponent(c.name)}
                      className="p-3.5 bg-slate-50 dark:bg-[#0d0f17] border-2 border-black dark:border-slate-800 hover:border-sky-500 dark:hover:border-sky-500 transition-all cursor-pointer space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none group"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-xs text-black dark:text-white truncate group-hover:text-sky-400 transition-colors">
                          {c.name}
                        </span>
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 border border-black dark:border-slate-700 bg-white dark:bg-[#181a24] text-slate-700 dark:text-slate-300 shrink-0">
                          {c.stereotype}
                        </span>
                      </div>

                      {rawComp?.file && (
                        <div className="text-[10px] font-mono text-slate-500 truncate">
                          {rawComp.file}
                        </div>
                      )}

                      {deps.length > 0 && (
                        <div className="pt-2 border-t border-black/10 dark:border-slate-800/80 font-mono text-[10px]">
                          <span className="text-slate-500 block mb-1">➔ Injected Dependencies ({deps.length}):</span>
                          <div className="flex flex-wrap gap-1">
                            {deps.slice(0, 3).map((dep: string) => (
                              <span key={dep} className="px-1.5 py-0.2 bg-sky-100 dark:bg-sky-950/60 text-sky-900 dark:text-sky-300 border border-sky-300 dark:border-sky-800 rounded-none">
                                {dep}
                              </span>
                            ))}
                            {deps.length > 3 && (
                              <span className="text-slate-500">+{deps.length - 3} more</span>
                            )}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-1 text-[10px] text-sky-600 dark:text-sky-400 font-bold">
                        <span>{methods.length} methods declared</span>
                        <span className="group-hover:translate-x-1 transition-transform">Inspect Evidence ➔</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Slide-Over Component Inspector Drawer */}
      <ComponentInspectorDrawer
        componentName={inspectedComponent}
        analysisRunId={data.analysis_run_id}
        onClose={() => setInspectedComponent(null)}
        onSelectComponent={(name) => setInspectedComponent(name)}
        onNavigateTab={onNavigateTab}
      />
    </div>
  );
};
