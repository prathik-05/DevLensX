import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  GitFork,
  ArrowRight,
  FileCode,
  ShieldCheck,
  Cpu,
  Zap,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { fetchComponentDetails, resolveEvidence } from '../apiClient';
import { SourceViewer } from './SourceViewer';
import { EvidenceBadge } from './EvidenceBadge';
import type { Verdict, ResolvedEvidence } from '../evidence';

interface ComponentInspectorDrawerProps {
  componentName: string | null;
  analysisRunId?: string;
  onClose: () => void;
  onSelectComponent?: (name: string) => void;
  onNavigateTab?: (tab: string, query?: string) => void;
}

export const ComponentInspectorDrawer: React.FC<ComponentInspectorDrawerProps> = ({
  componentName,
  analysisRunId,
  onClose,
  onSelectComponent,
  onNavigateTab,
}) => {
  const [details, setDetails] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'methods' | 'graph' | 'source'>('overview');
  const [resolvedSource, setResolvedSource] = useState<ResolvedEvidence | null>(null);
  const [resolvingSource, setResolvingSource] = useState<boolean>(false);

  useEffect(() => {
    if (!componentName) {
      setDetails(null);
      setResolvedSource(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setResolvedSource(null);

    async function loadDetails() {
      try {
        const res = await fetchComponentDetails(componentName!, analysisRunId);
        if (!cancelled && res && res.status === 'success') {
          setDetails(res);
        }
      } catch (err) {
        console.warn('Failed to load component details:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDetails();
    return () => {
      cancelled = true;
    };
  }, [componentName, analysisRunId]);

  if (!componentName) return null;

  const handleOpenSource = async () => {
    if (!details?.file_path || resolvingSource) return;
    setResolvingSource(true);
    try {
      const ref = {
        repository_id: 'repo',
        analysis_run_id: analysisRunId || 'run',
        file_path: details.file_path,
        line_start: details.line_start || 1,
        line_end: details.line_end || details.line_start || 1,
        symbol_name: details.symbol_name || componentName,
        evidence_type: 'AST' as const,
      };
      const resolved = await resolveEvidence(ref);
      setResolvedSource(resolved);
      setActiveTab('source');
    } catch (err) {
      console.warn('Failed to resolve source:', err);
    } finally {
      setResolvingSource(false);
    }
  };

  const incoming = details?.incoming_callers || [];
  const outgoing = details?.outgoing_dependencies || [];
  const methods = details?.methods || [];
  const blastRadius = details?.blast_radius || [];

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-white dark:bg-[#0c0e14] border-l-2 border-black dark:border-slate-800 shadow-[-8px_0px_24px_rgba(0,0,0,0.25)] flex flex-col font-sans transition-all duration-200"
      role="dialog"
      aria-modal="true"
      aria-label={`Component details for ${componentName}`}
    >
      {/* Slide-over Header */}
      <div className="p-4 border-b-2 border-black dark:border-slate-800 bg-slate-50 dark:bg-[#12151f] flex items-center justify-between gap-3">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="p-2 border-2 border-black dark:border-sky-500 bg-sky-100 dark:bg-sky-950 text-sky-900 dark:text-sky-200 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none flex-shrink-0">
            <Layers className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-black text-black dark:text-white truncate tracking-tight">
                {details?.symbol_name || componentName}
              </h2>
              {details?.stereotype && (
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 text-black dark:text-slate-200 border border-black dark:border-slate-600 uppercase">
                  {details.stereotype}
                </span>
              )}
            </div>
            {details?.file_path && (
              <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400 truncate">
                {details.file_path}:{details.line_start || 1}-{details.line_end || details.line_start || 1}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          <EvidenceBadge verdict={(details?.verdict || 'VERIFIED') as Verdict} compact />
          <button
            onClick={onClose}
            className="p-1.5 border border-black dark:border-slate-700 bg-white dark:bg-[#181a24] text-black dark:text-white hover:bg-slate-200 dark:hover:bg-slate-800 transition-all shadow-[2px_2px_0px_0px_#000000] dark:shadow-none"
            aria-label="Close component inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center border-b-2 border-black dark:border-slate-800 bg-white dark:bg-[#0c0e14] px-4 font-mono text-xs">
        <button
          onClick={() => setActiveTab('overview')}
          className={`py-2.5 px-3 border-b-2 font-bold transition-all ${
            activeTab === 'overview'
              ? 'border-black dark:border-sky-500 text-black dark:text-white'
              : 'border-transparent text-slate-500 hover:text-black dark:hover:text-white'
          }`}
        >
          Overview & Responsibility
        </button>
        <button
          onClick={() => setActiveTab('methods')}
          className={`py-2.5 px-3 border-b-2 font-bold transition-all ${
            activeTab === 'methods'
              ? 'border-black dark:border-sky-500 text-black dark:text-white'
              : 'border-transparent text-slate-500 hover:text-black dark:hover:text-white'
          }`}
        >
          Methods ({methods.length})
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`py-2.5 px-3 border-b-2 font-bold transition-all ${
            activeTab === 'graph'
              ? 'border-black dark:border-sky-500 text-black dark:text-white'
              : 'border-transparent text-slate-500 hover:text-black dark:hover:text-white'
          }`}
        >
          Graph Relations ({incoming.length + outgoing.length})
        </button>
        {resolvedSource && (
          <button
            onClick={() => setActiveTab('source')}
            className={`py-2.5 px-3 border-b-2 font-bold transition-all ${
              activeTab === 'source'
                ? 'border-black dark:border-sky-500 text-black dark:text-white'
                : 'border-transparent text-slate-500 hover:text-black dark:hover:text-white'
            }`}
          >
            Source Code
          </button>
        )}
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {loading ? (
          <div className="py-16 text-center space-y-3 font-mono text-xs text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#0284c7]" />
            <p>Inspecting component AST and Kùzu graph relations…</p>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="space-y-4">
                {/* Responsibility Card */}
                <div className="border-2 border-black dark:border-slate-800 bg-slate-50 dark:bg-[#12151f] p-4 space-y-2 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
                  <div className="flex items-center space-x-2 text-xs font-black uppercase text-black dark:text-white">
                    <Cpu className="w-4 h-4 text-[#0284c7]" />
                    <span>Architectural Responsibility</span>
                  </div>
                  <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                    {details?.responsibility || details?.explanation || 'No docstring or explicit summary recorded.'}
                  </div>
                </div>

                {/* Grounded Provenance Box */}
                {details?.citations && details.citations.length > 0 && (
                  <div className="border border-black dark:border-slate-800 p-3 bg-white dark:bg-[#10121a] space-y-1.5 font-mono text-xs">
                    <span className="text-[10px] text-slate-500 uppercase font-black block">Line-Level Evidence Citation</span>
                    <div className="flex flex-wrap gap-2">
                      {details.citations.map((cite: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 bg-sky-50 dark:bg-sky-950/50 border border-black dark:border-sky-600 text-sky-900 dark:text-sky-300 font-bold text-[11px]"
                        >
                          Sources: [{cite}]()
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Callers & Dependencies Quick Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
                  {/* Used By (Callers) */}
                  <div className="p-3 border-2 border-black dark:border-slate-800 bg-white dark:bg-[#10121a] space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
                    <div className="flex items-center justify-between text-[11px] font-black uppercase text-black dark:text-white border-b border-black/20 dark:border-slate-800 pb-1.5">
                      <span className="flex items-center gap-1.5">
                        <GitFork className="w-3.5 h-3.5 text-sky-500" />
                        <span>Used By ({incoming.length})</span>
                      </span>
                    </div>
                    {incoming.length > 0 ? (
                      <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
                        {incoming.map((c: any, i: number) => (
                          <button
                            key={i}
                            onClick={() => onSelectComponent?.(c.caller || c.name)}
                            className="text-left px-2 py-1 bg-slate-50 dark:bg-slate-900 hover:bg-sky-100 dark:hover:bg-sky-900/40 border border-slate-300 dark:border-slate-700 transition-colors flex items-center justify-between group"
                          >
                            <span className="font-bold text-black dark:text-white truncate">{c.caller || c.name}</span>
                            <span className="text-[9px] text-slate-500 group-hover:text-black dark:group-hover:text-white">
                              {c.relation || 'CALLS'} →
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-500 py-1 italic">Root entrypoint or uninvoked unit.</div>
                    )}
                  </div>

                  {/* Uses (Dependencies) */}
                  <div className="p-3 border-2 border-black dark:border-slate-800 bg-white dark:bg-[#10121a] space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
                    <div className="flex items-center justify-between text-[11px] font-black uppercase text-black dark:text-white border-b border-black/20 dark:border-slate-800 pb-1.5">
                      <span className="flex items-center gap-1.5">
                        <ArrowRight className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Uses ({outgoing.length})</span>
                      </span>
                    </div>
                    {outgoing.length > 0 ? (
                      <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
                        {outgoing.map((d: any, i: number) => (
                          <button
                            key={i}
                            onClick={() => onSelectComponent?.(d.dependency || d.name)}
                            className="text-left px-2 py-1 bg-slate-50 dark:bg-slate-900 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 border border-slate-300 dark:border-slate-700 transition-colors flex items-center justify-between group"
                          >
                            <span className="font-bold text-black dark:text-white truncate">{d.dependency || d.name}</span>
                            <span className="text-[9px] text-slate-500 group-hover:text-black dark:group-hover:text-white">
                              {d.relation || 'DEPENDS_ON'} →
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-500 py-1 italic">Leaf component (no external dependencies).</div>
                    )}
                  </div>
                </div>

                {/* Downstream Blast Radius Risk */}
                {blastRadius.length > 0 && (
                  <div className="border border-amber-500/50 bg-amber-50 dark:bg-amber-950/20 p-3.5 space-y-2 font-mono text-xs">
                    <div className="flex items-center space-x-1.5 text-amber-800 dark:text-amber-300 font-black uppercase text-[11px]">
                      <AlertCircle className="w-4 h-4" />
                      <span>Downstream Blast Radius ({blastRadius.length} components)</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {blastRadius.map((b: string, i: number) => (
                        <button
                          key={i}
                          onClick={() => onSelectComponent?.(b)}
                          className="px-2 py-0.5 bg-white dark:bg-slate-900 border border-amber-600/40 text-black dark:text-amber-200 text-[10px] font-bold hover:bg-amber-100 dark:hover:bg-amber-900/40"
                        >
                          {b}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'methods' && (
              <div className="space-y-3 font-mono text-xs">
                <div className="text-slate-600 dark:text-slate-400 text-[11px]">
                  Declared methods & parameter contracts verified from parsed AST:
                </div>
                {methods.length > 0 ? (
                  <div className="border-2 border-black dark:border-slate-800 divide-y-2 divide-black dark:divide-slate-800 bg-white dark:bg-[#10121a]">
                    {methods.map((m: any, i: number) => (
                      <div key={i} className="p-3 space-y-1 hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-black dark:text-sky-300 text-xs truncate">{m.name}()</span>
                          <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-[10px] text-slate-700 dark:text-slate-300 border border-black dark:border-slate-700">
                            {m.return_type || 'void'}
                          </span>
                        </div>
                        {m.parameters && m.parameters.length > 0 && (
                          <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                            params: ({m.parameters.join(', ')})
                          </div>
                        )}
                        {m.line_number && (
                          <div className="text-[9px] text-slate-400">
                            Declared at line {m.line_number}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 border border-dashed border-slate-400 text-center text-slate-500">
                    No explicit methods parsed for this component.
                  </div>
                )}
              </div>
            )}

            {activeTab === 'graph' && (
              <div className="space-y-4 font-mono text-xs">
                <div className="space-y-2">
                  <h4 className="font-bold uppercase text-[11px] text-black dark:text-white">
                    Inbound Callers (Who invokes {componentName}):
                  </h4>
                  {incoming.length > 0 ? (
                    <div className="border border-black dark:border-slate-800 divide-y divide-slate-200 dark:divide-slate-800">
                      {incoming.map((c: any, i: number) => (
                        <div key={i} className="p-2.5 flex items-center justify-between bg-white dark:bg-[#10121a]">
                          <span className="font-bold text-black dark:text-white">{c.caller || c.name}</span>
                          <span className="text-[10px] px-2 py-0.5 bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300 font-bold">
                            {c.relation || 'CALLS'}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-500 italic">No inbound callers in graph.</div>
                  )}
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <h4 className="font-bold uppercase text-[11px] text-black dark:text-white">
                    Outbound Dependencies (Who {componentName} relies upon):
                  </h4>
                  {outgoing.length > 0 ? (
                    <div className="border border-black dark:border-slate-800 divide-y divide-slate-200 dark:divide-slate-800">
                      {outgoing.map((d: any, i: number) => (
                        <div key={i} className="p-2.5 flex items-center justify-between bg-white dark:bg-[#10121a]">
                          <span className="font-bold text-black dark:text-white">{d.dependency || d.name}</span>
                          <span className="text-[10px] px-2 py-0.5 bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold">
                            {d.relation || 'DEPENDS_ON'}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-500 italic">No outbound dependencies in graph.</div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'source' && resolvedSource && (
              <div className="pt-2">
                <SourceViewer evidence={resolvedSource} onClose={() => setActiveTab('overview')} />
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t-2 border-black dark:border-slate-800 bg-slate-50 dark:bg-[#12151f] flex flex-wrap items-center gap-2">
        <button
          onClick={handleOpenSource}
          disabled={resolvingSource || !details?.file_path}
          className="px-3.5 py-1.5 bg-black dark:bg-sky-600 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none hover:bg-neutral-800 dark:hover:bg-sky-500 disabled:opacity-50 transition-all"
        >
          <FileCode className="w-3.5 h-3.5" />
          <span>{resolvingSource ? 'Resolving Evidence…' : 'Open Source'}</span>
        </button>

        {onNavigateTab && (
          <>
            <button
              onClick={() => onNavigateTab('changelog', details?.symbol_name || componentName)}
              className="px-3 py-1.5 bg-white dark:bg-[#181a24] text-black dark:text-white border-2 border-black dark:border-slate-700 font-mono text-xs font-bold flex items-center gap-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none transition-all"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Change Impact</span>
            </button>

            <button
              onClick={() =>
                onNavigateTab(
                  'ai-assistant',
                  `Explain the architectural design, patterns, and integration points for component ${details?.symbol_name || componentName}.`
                )
              }
              className="px-3 py-1.5 bg-white dark:bg-[#181a24] text-black dark:text-white border-2 border-black dark:border-slate-700 font-mono text-xs font-bold flex items-center gap-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none transition-all"
            >
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              <span>Ask AI Chat</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
};
