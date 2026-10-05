import React, { useState } from 'react';
import {
  Bug,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  GitFork,
  Loader2,
  Zap,
  Info
} from 'lucide-react';
import { useAppStore } from '../store';
import { SourceViewer, useEvidenceResolver } from './SourceViewer';
import { resolveEvidence } from '../apiClient';

interface VerifiedLocation {
  class_name: string;
  file: string;
  line: number;
  method: string;
  status: string;
}

interface VerifiedDependency {
  source: string;
  target: string;
  relationship: string;
  status: string;
}

interface DebugAnalysisResponse {
  status: string;
  exception_type: string;
  verified_locations: VerifiedLocation[];
  verified_dependencies: VerifiedDependency[];
  ai_hypothesis: {
    text: string;
    badge: string;
  };
  not_verified_boundary: {
    text: string;
    badge: string;
  };
}

export const DebugView: React.FC = () => {
  const data = useAppStore((s) => s.analysisData);
  const [stackTrace, setStackTrace] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<DebugAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { evidence, setEvidence, loading: resolvingSource, setLoading: setResolvingSource } = useEvidenceResolver();

  const handleAnalyze = async () => {
    if (!stackTrace.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/debug/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stack_trace: stackTrace }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        setError('Debug analysis failed. Ensure the stack trace contains valid error lines.');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to connect to Debug Engine backend.');
    } finally {
      setLoading(false);
    }
  };

  const loadExampleTrace = () => {
    setStackTrace(
`java.lang.NullPointerException: Cannot invoke "org.springframework.samples.petclinic.owner.Owner.getFirstName()" because "owner" is null
\tat org.springframework.samples.petclinic.owner.OwnerController.processFindForm(OwnerController.java:110)
\tat org.springframework.samples.petclinic.owner.OwnerController.initCreationForm(OwnerController.java:85)
\tat org.springframework.samples.petclinic.owner.PetClinicApplication.main(PetClinicApplication.java:32)`
    );
  };

  const handleOpenSource = async (loc: VerifiedLocation) => {
    if (!loc.file || resolvingSource) return;
    setResolvingSource(true);
    try {
      const ref = {
        repository_id: data?.repository || 'repo',
        analysis_run_id: data?.analysis_run_id || 'run',
        file_path: loc.file,
        line_start: Math.max(1, loc.line - 5),
        line_end: loc.line + 15,
        symbol_name: loc.class_name,
        evidence_type: 'AST' as const,
      };
      const resolved = await resolveEvidence(ref);
      setEvidence(resolved);
    } catch (err) {
      console.warn('Failed to resolve evidence:', err);
    } finally {
      setResolvingSource(false);
    }
  };

  return (
    <div className="space-y-6 font-sans bg-white dark:bg-[#0a0a0f] text-black dark:text-[#f8fafc]">
      {/* Header */}
      <div className="border-b-2 border-black dark:border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-rose-100 text-rose-900 dark:bg-rose-950/60 dark:text-rose-300 border-2 border-black dark:border-rose-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              ROOT CAUSE CENTER
            </span>
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-2 border-black dark:border-emerald-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              ● AST & GRAPH GROUNDED
            </span>
          </div>
          <h1 className="text-2xl font-black text-black dark:text-white flex items-center space-x-2 tracking-tight">
            <Bug className="w-6 h-6 text-rose-600 dark:text-rose-400" />
            <span>Debug Center & Stack Trace Grounding</span>
          </h1>
          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium mt-1">
            Map runtime exceptions and crash stack traces directly to verified codebase AST nodes and dependency graph edges.
          </p>
        </div>

        <button
          onClick={loadExampleTrace}
          className="px-3 py-1.5 bg-white dark:bg-[#181a24] text-black dark:text-white border-2 border-black dark:border-slate-700 font-mono text-xs font-bold hover:bg-slate-100 dark:hover:bg-slate-800 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none transition-all"
        >
          Load Example Trace
        </button>
      </div>

      {/* Input Area */}
      <div className="border-2 border-black dark:border-slate-800 bg-slate-50 dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
        <label className="text-xs font-black uppercase text-black dark:text-white block">
          Paste Application Stack Trace:
        </label>
        <textarea
          value={stackTrace}
          onChange={(e) => setStackTrace(e.target.value)}
          placeholder="Paste raw stack trace here (e.g. java.lang.NullPointerException at com.example.Controller.method(Controller.java:42)...)"
          rows={6}
          className="w-full p-3 font-mono text-xs bg-white dark:bg-[#0c0e14] border-2 border-black dark:border-slate-700 text-black dark:text-white outline-none resize-y"
        />
        <div className="flex justify-end">
          <button
            onClick={handleAnalyze}
            disabled={loading || !stackTrace.trim()}
            className="px-5 py-2 bg-black dark:bg-rose-600 text-white font-mono text-xs font-black shadow-[2px_2px_0px_0px_#000000] dark:shadow-none hover:bg-neutral-800 dark:hover:bg-rose-500 disabled:opacity-50 transition-all flex items-center gap-1.5"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Analyze & Map to Graph</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 border-2 border-rose-600 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 text-xs font-mono font-bold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Results View */}
      {result && result.status === 'success' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Grounding Header Card */}
          <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-4 flex flex-wrap items-center justify-between gap-3 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <div>
                <span className="font-sans text-xs font-black uppercase text-black dark:text-white">
                  Exception: {result.exception_type}
                </span>
                <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
                  {result.verified_locations.length} codebase locations statically mapped to repository AST
                </p>
              </div>
            </div>
            <span className="px-2.5 py-1 text-[10px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-300 border border-black dark:border-emerald-600 uppercase">
              TRACE GROUNDED
            </span>
          </div>

          {/* Verified Locations Table */}
          <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-5 space-y-4 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
            <div className="flex items-center space-x-2 border-b-2 border-black dark:border-slate-800 pb-3">
              <FileCode className="w-4 h-4 text-[#0284c7]" />
              <h2 className="text-xs font-black uppercase text-black dark:text-white">
                Statically Verified Code Locations (AST)
              </h2>
            </div>
            <div className="space-y-2 font-mono text-xs">
              {result.verified_locations.map((loc, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 dark:bg-[#181a24] border border-black dark:border-slate-700 flex flex-wrap items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <div className="font-bold text-black dark:text-white text-xs truncate">
                      {loc.class_name}.{loc.method}()
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400">
                      {loc.file} : Line {loc.line}
                    </div>
                  </div>
                  <button
                    onClick={() => handleOpenSource(loc)}
                    className="px-3 py-1 bg-black dark:bg-sky-600 text-white text-[11px] font-bold hover:bg-neutral-800 dark:hover:bg-sky-500 transition-all flex items-center gap-1 shadow-[1px_1px_0px_0px_#000000] dark:shadow-none"
                  >
                    <FileCode className="w-3 h-3" />
                    <span>Open Line {loc.line}</span>
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Graph Dependencies Along Trace */}
          {result.verified_dependencies.length > 0 && (
            <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-5 space-y-4 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center space-x-2 border-b-2 border-black dark:border-slate-800 pb-3">
                <GitFork className="w-4 h-4 text-sky-500" />
                <h2 className="text-xs font-black uppercase text-black dark:text-white">
                  Knowledge Graph Call Path (Kùzu Edge Provenance)
                </h2>
              </div>
              <div className="flex flex-wrap gap-2 font-mono text-xs">
                {result.verified_dependencies.map((dep, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-50 dark:bg-[#181a24] border border-black dark:border-slate-700 flex items-center gap-2"
                  >
                    <span className="font-bold text-black dark:text-white">{dep.source}</span>
                    <span className="text-[10px] text-sky-600 dark:text-sky-400 font-bold">
                      --[{dep.relationship}]--&gt;
                    </span>
                    <span className="font-bold text-black dark:text-white">{dep.target}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Root Cause Hypothesis & Grounding Boundary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* AI Hypothesis */}
            <div className="border-2 border-black dark:border-sky-500 bg-white dark:bg-[#12131a] p-4 space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b border-black/20 dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-sky-700 dark:text-sky-300 flex items-center gap-1">
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  <span>AI Root Cause Hypothesis</span>
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-sky-100 dark:bg-sky-950 text-sky-900 dark:text-sky-300 border border-black dark:border-sky-600">
                  AI SUGGESTION
                </span>
              </div>
              <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                {result.ai_hypothesis.text}
              </p>
            </div>

            {/* Boundary */}
            <div className="border-2 border-black dark:border-slate-700 bg-white dark:bg-[#12131a] p-4 space-y-2 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b border-black/20 dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-slate-500" />
                  <span>Runtime Verification Boundary</span>
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-black dark:border-slate-600">
                  NOT VERIFIED
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {result.not_verified_boundary.text}
              </p>
            </div>
          </div>

          {/* Inline Source Viewer */}
          {evidence && (
            <div className="pt-2">
              <SourceViewer evidence={evidence} onClose={() => setEvidence(null)} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
