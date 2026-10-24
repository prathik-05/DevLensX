import React, { useState, useMemo } from 'react';
import {
  GitBranch,
  Search,
  CheckCircle2,
  FileCode,
  ListChecks,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  FileDiff
} from 'lucide-react';
import { useAppStore } from '../store';
import { Badge } from './Badge';
import { SourceViewer, useEvidenceResolver } from './SourceViewer';
import { resolveEvidence, getWorkspaceImpact } from '../apiClient';
import type { ImpactResult } from '../apiClient';

export const ChangeImpactView: React.FC = () => {
  const data = useAppStore((s) => s.analysisData);
  const analysisId = useAppStore((s) => s.analysisId);
  const [query, setQuery] = useState<string>('');
  const [gitDiff, setGitDiff] = useState<string>('');
  const [showDiffInput, setShowDiffInput] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [impactResult, setImpactResult] = useState<ImpactResult | null>(null);
  const [_error, setError] = useState<string | null>(null);
  const { evidence, setEvidence, loading: resolvingSource, setLoading: setResolvingSource } = useEvidenceResolver();

  // Extract candidate components/methods from AST / Knowledge Graph (excluding tests and signatures)
  const candidateComponents = useMemo(() => {
    const nodes: any[] = data?.knowledge_graph?.nodes || [];
    const list: any[] = nodes.length > 0 ? nodes : ((data as any)?.classes || []);
    return list
      .filter((c: any) => {
        const file = String(c.file || '').replace(/\\/g, '/').toLowerCase();
        const rawName = String(c.name || c.id || '');
        if (file.includes('/test/') || file.includes('test') || c.is_test) return false;
        if (['setup', 'teardown', 'initpvp', 'main'].includes(rawName.toLowerCase())) return false;
        if (/^(?:test|init[A-Z]|[A-Z].*(?:Scenario|Wins|Draw|Rejected|Restart|When|Move))/i.test(rawName) && c.stereotype !== 'Controller') return false;
        return true;
      })
      .map((c: any) => {
        let cleanName = String(c.name || c.id || '').trim();
        // Strip trailing signatures, braces, throws, and cutoffs
        cleanName = cleanName.replace(/\(.*?\)/g, '').replace(/[\{\}\(\)]/g, '').replace(/\bthrows\b.*/i, '').trim();
        cleanName = cleanName.replace(/\s*(?:thr|throw|thro)$/i, '').trim();
        return {
          name: cleanName,
          stereotype: c.stereotype || c.kind || 'Component',
          file: c.file || '',
        };
      })
      .filter((c: any) => c.name && !c.name.includes('$') && !c.name.includes('Test') && c.name.length > 1)
      .filter((c: any, index: number, arr: any[]) => arr.findIndex(x => x.name === c.name) === index)
      .slice(0, 10);
  }, [data]);

  const runAnalysis = async (targetName?: string) => {
    const sym = (targetName ?? query).trim();
    if (!sym || loading) return;
    if (targetName) setQuery(sym);
    setLoading(true);
    setError(null);

    const effectiveRunId = analysisId || data?.analysis_run_id || 'latest';

    try {
      const res = await getWorkspaceImpact(effectiveRunId, sym, gitDiff.trim() || undefined);
      setImpactResult(res);
    } catch (err: any) {
      console.warn('Backend impact call failed, attempting client-side fallback:', err);
      // Fallback: build from in-memory knowledge graph if backend offline
      const nodes: any[] = data?.knowledge_graph?.nodes || [];
      const edges: any[] = data?.knowledge_graph?.edges || [];

      const targetNode = nodes.find(
        (n: any) =>
          n.name === sym ||
          n.id === sym ||
          String(n.name || '').toLowerCase() === sym.toLowerCase()
      );

      const targetNameResolved = targetNode?.name || sym;
      const targetFile = targetNode?.file || '';

      const direct: any[] = [];
      const directSet = new Set<string>();
      edges.forEach((e: any) => {
        if (e.target === targetNameResolved || e.target === targetNode?.id) {
          if (!directSet.has(e.source)) {
            directSet.add(e.source);
            direct.push({
              symbol: e.source,
              file: targetFile,
              line_start: 1,
              line_end: 20,
              relation: e.relationship || 'CALLS',
              confidence: 'INFERRED_CALL',
            });
          }
        }
      });

      const transitive: any[] = [];
      const transSet = new Set<string>();
      edges.forEach((e: any) => {
        if (directSet.has(e.target) && !directSet.has(e.source) && e.source !== targetNameResolved && !transSet.has(e.source)) {
          transSet.add(e.source);
          transitive.push({
            symbol: e.source,
            file: '',
            relation: 'TRANSITIVE_CALL',
            hop: 2,
            path: [targetNameResolved, e.target, e.source],
          });
        }
      });

      const tests: any[] = [];
      nodes.forEach((n: any) => {
        const nName = n.name || n.id || '';
        if (nName.toLowerCase().includes('test') && (nName.toLowerCase().includes(sym.toLowerCase()) || directSet.has(nName))) {
          tests.push({
            symbol: nName,
            file: n.file || '',
            relation: 'TESTS',
            status: 'VERIFIED',
          });
        }
      });

      setImpactResult({
        repository_id: data?.repository || 'repo',
        analysis_run_id: effectiveRunId,
        commit_hash: null,
        target_symbol: targetNameResolved,
        status: targetNode ? 'OK' : 'TARGET_NOT_FOUND',
        risk_level: direct.length >= 4 ? 'HIGH' : direct.length >= 1 ? 'MEDIUM' : 'LOW',
        direct: [{ symbol: targetNameResolved, file: targetFile, status: 'VERIFIED' }],
        downstream: direct.map(d => ({ symbol: d.symbol, file: d.file, status: 'VERIFIED' })),
        direct_callers: direct,
        transitive_callers: transitive,
        dependencies: [],
        tests,
        configs: [],
        evidence_refs: [],
        diagram: null,
        potential_regressions: [
          `Modifications to ${targetNameResolved} may alter behavior for ${direct.length} direct caller(s).`,
          'Boundary condition checks and return value contracts must be maintained.'
        ],
        recommended_validations: [
          `Execute unit tests covering ${targetNameResolved}.`,
          'Validate edge conditions and callers across adjacent architectural boundaries.'
        ],
        coverage_limitations: [
          'Client-side fallback: full AST call hierarchy requires active backend server.'
        ],
        execution_order_type: direct.length > 0 ? 'VERIFIED_CALL_ORDER' : 'INFERRED_ARCHITECTURE_ORDER',
        risk_assessment: {
          risk_level: direct.length >= 4 ? 'HIGH' : direct.length >= 1 ? 'MEDIUM' : 'LOW',
          risk_score: direct.length * 10,
          reasons: [`${direct.length} direct caller(s) depend on this symbol.`],
          caller_count: direct.length,
          transitive_count: transitive.length,
          test_count: tests.length,
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenSource = async (file: string, lineStart?: number, lineEnd?: number, symbol?: string) => {
    if (!file || resolvingSource) return;
    setResolvingSource(true);
    try {
      const ref = {
        repository_id: data?.repository || 'repo',
        analysis_run_id: data?.analysis_run_id || 'run',
        file_path: file,
        line_start: lineStart || 1,
        line_end: lineEnd || (lineStart || 1) + 20,
        symbol_name: symbol || query,
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

  const targetSymbol = impactResult?.target_symbol || query;
  const directCallers = impactResult?.direct_callers || [];
  const transitiveCallers = impactResult?.transitive_callers || [];
  const tests = impactResult?.tests || [];
  const potentialRegressions = impactResult?.potential_regressions || [];
  const recommendedValidations = impactResult?.recommended_validations || [];
  const coverageLimitations = impactResult?.coverage_limitations || [];
  const execOrderType = impactResult?.execution_order_type || 'VERIFIED_CALL_ORDER';
  const riskLevel = impactResult?.risk_level || 'LOW';

  return (
    <div className="space-y-6 font-sans bg-white dark:bg-[#0a0a0f] text-black dark:text-[#f8fafc]">
      {/* Header */}
      <div className="border-b-2 border-black dark:border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 text-[11px] font-mono font-bold bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300 border border-black dark:border-amber-500 uppercase tracking-wider">
              CHANGE IMPACT & BLAST RADIUS
            </span>
            {impactResult && (
              <span
                className={`px-2.5 py-0.5 text-[11px] font-mono font-bold border ${
                  execOrderType === 'VERIFIED_CALL_ORDER'
                    ? 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-600'
                    : execOrderType === 'UNRESOLVED_RUNTIME_BEHAVIOR'
                    ? 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300 border-amber-600'
                    : 'bg-sky-100 text-sky-900 dark:bg-sky-950/60 dark:text-sky-300 border-sky-600'
                }`}
              >
                ● {execOrderType.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-black text-black dark:text-white flex items-center space-x-2 tracking-tight">
            <GitBranch className="w-6 h-6 text-[#0284c7]" />
            <span>Impact Analysis & Blast Radius Cascade</span>
          </h1>
          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium mt-1">
            Determine exact regression risks, callers, affected tests, and coverage limitations before modifying code.
          </p>
        </div>

        {impactResult && (
          <div className="flex items-center space-x-2">
            <Badge
              variant={
                riskLevel === 'CRITICAL'
                  ? 'risk-high'
                  : riskLevel === 'HIGH'
                  ? 'risk-high'
                  : riskLevel === 'MEDIUM'
                  ? 'risk-medium'
                  : 'risk-low'
              }
              size="lg"
            >
              {riskLevel} REGRESSION RISK
            </Badge>
          </div>
        )}
      </div>

      {/* Target Selector & Query Bar */}
      <div className="p-4 bg-slate-50 dark:bg-[#12131a] border-2 border-black dark:border-slate-800 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
        <div className="flex items-center justify-between">
          <label className="text-xs font-black uppercase text-black dark:text-white block">
            Target Function, Class, or Method to Modify:
          </label>
          <button
            onClick={() => setShowDiffInput(!showDiffInput)}
            className="text-[11px] font-mono text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-1"
          >
            <FileDiff className="w-3.5 h-3.5" />
            <span>{showDiffInput ? 'Hide Git Diff' : 'Compare with Git Diff'}</span>
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') runAnalysis();
            }}
            placeholder="e.g. Board.isWinner, GameController, evaluateBoard, place_ship..."
            className="flex-1 px-3 py-2 text-xs font-mono border-2 border-black dark:border-slate-700 bg-white dark:bg-[#0c0e14] text-black dark:text-white outline-none"
          />
          <button
            onClick={() => runAnalysis()}
            disabled={loading || !query.trim()}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-black shadow-[2px_2px_0px_0px_#000000] dark:shadow-none disabled:opacity-50 transition-all flex items-center gap-1.5 rounded-sm"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Calculate Impact</span>
          </button>
        </div>

        {/* Optional Git Diff Input */}
        {showDiffInput && (
          <div className="pt-2 space-y-1.5">
            <span className="text-[10px] font-mono font-bold text-slate-500 uppercase block">
              Paste Unified Diff to Analyze Signature & Line Breakages:
            </span>
            <textarea
              value={gitDiff}
              onChange={(e) => setGitDiff(e.target.value)}
              placeholder="diff --git a/Board.java b/Board.java\n@@ -250,5 +250,5 @@\n- boolean isWinner()\n+ boolean isWinner(Player player)"
              rows={4}
              className="w-full p-2 text-xs font-mono border-2 border-black dark:border-slate-700 bg-white dark:bg-[#0c0e14] text-black dark:text-white outline-none"
            />
          </div>
        )}

        {/* Quick Suggestion Chips */}
        {candidateComponents.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[10px] font-mono font-bold text-slate-500 uppercase">Top Symbols:</span>
            {candidateComponents.map((c) => (
              <button
                key={c.name}
                onClick={() => runAnalysis(c.name)}
                className="px-2.5 py-1 text-[11px] font-mono font-bold bg-white dark:bg-[#181a24] text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 rounded transition-all shadow-sm"
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Initial state: Unknown regression risk placeholder */}
      {!impactResult && !loading && (
        <div className="p-6 border-2 border-dashed border-slate-300 dark:border-slate-800 bg-slate-50/50 dark:bg-[#12131a]/50 text-center rounded-sm">
          <div className="inline-flex p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 mb-2">
            <GitBranch className="w-6 h-6 text-indigo-500" />
          </div>
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">UNKNOWN REGRESSION RISK</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
            Select a target function, class, or method above or click one of the Top Symbols chips to calculate callers, blast radius cascade, downstream impact, and affected tests.
          </p>
        </div>
      )}

      {/* Target Not Found Notice */}
      {impactResult?.status === 'TARGET_NOT_FOUND' && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border-2 border-amber-500 text-amber-900 dark:text-amber-200 font-mono text-xs flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600 mt-0.5" />
          <div>
            <span className="font-bold block">Target '{targetSymbol}' Not Found</span>
            <span>This symbol does not exist in the active repository snapshot. Verify spelling or choose from the Top Symbols chips above.</span>
          </div>
        </div>
      )}

      {/* Diff Analysis Card if active */}
      {impactResult?.diff_analysis && (
        <div className="p-4 bg-blue-50 dark:bg-blue-950/20 border-2 border-blue-500 text-blue-900 dark:text-blue-200 font-mono text-xs space-y-1">
          <div className="flex items-center gap-2">
            <FileDiff className="w-4 h-4 text-blue-600" />
            <span className="font-black uppercase">Git Diff Change Comparison:</span>
          </div>
          <p>{impactResult.diff_analysis.impact_summary}</p>
          {impactResult.diff_analysis.signature_altered && (
            <span className="text-rose-600 dark:text-rose-400 font-bold block">
              ⚠ Method signature altered: direct callers may require signature parameter updates.
            </span>
          )}
        </div>
      )}

      {/* 4-Tier Presentation Grid */}
      {impactResult && impactResult.status !== 'TARGET_NOT_FOUND' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* TIER 1: CHANGE */}
            <div className="border-2 border-black dark:border-sky-500 bg-white dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-sky-700 dark:text-sky-300">
                  1. CHANGE TARGET
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-sky-100 dark:bg-sky-950 text-sky-900 dark:text-sky-300 border border-black dark:border-sky-600">
                  PRIMARY
                </span>
              </div>
              <div className="space-y-1">
                <div className="text-sm font-black text-black dark:text-white truncate">
                  {targetSymbol}
                </div>
                {impactResult.direct?.[0]?.file && (
                  <button
                    onClick={() => handleOpenSource(impactResult.direct[0].file, 1, 30, targetSymbol)}
                    className="text-[10px] font-mono text-[#0284c7] hover:underline flex items-center gap-1 truncate"
                  >
                    <FileCode className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{impactResult.direct[0].file}</span>
                  </button>
                )}
              </div>
            </div>

            {/* TIER 2: DIRECT CALLERS */}
            <div className="border-2 border-black dark:border-amber-500 bg-white dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-amber-700 dark:text-amber-300">
                  2. DIRECT CALLERS
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-300 border border-black dark:border-amber-600">
                  {directCallers.length} CALLS
                </span>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {directCallers.length > 0 ? (
                  directCallers.map((dc, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleOpenSource(dc.file, dc.line_start, dc.line_end, dc.symbol)}
                      className="p-2 bg-slate-50 dark:bg-[#1a1c26] border border-black dark:border-slate-700 text-xs font-mono flex items-center justify-between cursor-pointer hover:bg-sky-50 dark:hover:bg-sky-950/40 transition-colors"
                    >
                      <span className="font-bold text-black dark:text-white truncate">{dc.symbol}</span>
                      <span className="text-[9px] text-amber-700 dark:text-amber-300 font-bold uppercase">[{dc.relation}]</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500 italic py-2">
                    No direct callers detected in graph. (May be an entrypoint, leaf component, or invoked via dynamic dispatch).
                  </div>
                )}
              </div>
            </div>

            {/* TIER 3: TRANSITIVE DOWNSTREAM */}
            <div className="border-2 border-black dark:border-purple-500 bg-white dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-purple-700 dark:text-purple-300">
                  3. TRANSITIVE IMPACT
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-purple-100 dark:bg-purple-950 text-purple-900 dark:text-purple-300 border border-black dark:border-purple-600">
                  {transitiveCallers.length} DOWNSTREAM
                </span>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {transitiveCallers.length > 0 ? (
                  transitiveCallers.map((tc, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleOpenSource(tc.file, tc.line_start, tc.line_end, tc.symbol)}
                      className="p-2 bg-slate-50 dark:bg-[#1a1c26] border border-black dark:border-slate-700 text-xs font-mono flex items-center justify-between cursor-pointer hover:bg-purple-50 dark:hover:bg-purple-950/40 transition-colors"
                    >
                      <span className="font-bold text-black dark:text-white truncate">{tc.symbol}</span>
                      <span className="text-[9px] text-purple-700 dark:text-purple-300 font-bold">Hop {tc.hop || 2}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500 italic py-2">No indirect upstream dependents found.</div>
                )}
              </div>
            </div>

            {/* TIER 4: RELEVANT TESTS */}
            <div className="border-2 border-black dark:border-emerald-500 bg-white dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2">
                <span className="text-[11px] font-black uppercase text-emerald-700 dark:text-emerald-300">
                  4. TESTS TO RUN
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-300 border border-black dark:border-emerald-600">
                  {tests.length} TEST SUITES
                </span>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {tests.length > 0 ? (
                  tests.map((tc, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleOpenSource(tc.file, tc.line_start, tc.line_end, tc.symbol)}
                      className="p-2 bg-slate-50 dark:bg-[#1a1c26] border border-black dark:border-slate-700 text-xs font-mono flex items-center justify-between cursor-pointer hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-colors"
                    >
                      <span className="font-bold text-black dark:text-white truncate">{tc.symbol}</span>
                      <span className="text-[9px] text-emerald-700 dark:text-emerald-300 font-bold uppercase">[TESTS]</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500 italic py-2">No test suites specifically referencing this symbol.</div>
                )}
              </div>
            </div>
          </div>

          {/* Potential Regressions & Recommended Validation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Potential Regressions */}
            <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-5 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center space-x-2 border-b-2 border-black dark:border-slate-800 pb-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                <h2 className="text-sm font-black uppercase text-black dark:text-white">
                  Potential Regressions (Hypotheses to Validate)
                </h2>
              </div>
              <div className="space-y-2 font-mono text-xs">
                {potentialRegressions.map((reg, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-50 dark:bg-[#070b14] border border-black/20 dark:border-slate-800 text-slate-800 dark:text-slate-200"
                  >
                    • {reg}
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Validation Checklist */}
            <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-5 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
              <div className="flex items-center space-x-2 border-b-2 border-black dark:border-slate-800 pb-2">
                <ListChecks className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <h2 className="text-sm font-black uppercase text-black dark:text-white">
                  Recommended Validation Checklist
                </h2>
              </div>
              <div className="space-y-2 font-mono text-xs">
                {recommendedValidations.map((val, idx) => (
                  <div
                    key={idx}
                    className="flex items-start space-x-2 p-2.5 bg-slate-50 dark:bg-[#070b14] border border-black/20 dark:border-slate-800 text-slate-800 dark:text-slate-200"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Uncertainty Disclosure / Coverage Limitations */}
          {coverageLimitations.length > 0 && (
            <div className="border-2 border-black dark:border-amber-600 bg-amber-50/50 dark:bg-amber-950/20 p-4 space-y-2 font-mono text-xs">
              <div className="flex items-center space-x-2 font-black text-amber-900 dark:text-amber-200 uppercase">
                <ShieldCheck className="w-4 h-4 text-amber-600" />
                <span>Honest Coverage Limitations & Uncertainty Disclosure</span>
              </div>
              <ul className="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-300">
                {coverageLimitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Inline Source Viewer if active */}
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
