import React, { useMemo } from 'react';
import { GlassPanel } from './GlassPanel';
import { Badge } from './Badge';
import { useAppStore } from '../store';
import { Skeleton } from './Skeleton';
import { Activity, AlertTriangle, Clock, Layers, Shield, ShieldCheck, Zap, TrendingUp, Info } from 'lucide-react';

interface OverviewViewProps {
  data?: any;
}

const gradeFor = (score: number | null) => {
  if (score === null || score === undefined) return { grade: '—', label: 'Not scored', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.1)', border: 'rgba(148, 163, 184, 0.25)', glow: 'none' };
  if (score >= 90) return { grade: 'A', label: 'Excellent', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.35)', glow: '0 0 16px rgba(16, 185, 129, 0.25)' };
  if (score >= 80) return { grade: 'B', label: 'Good', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.12)', border: 'rgba(6, 182, 212, 0.35)', glow: '0 0 16px rgba(6, 182, 212, 0.25)' };
  if (score >= 70) return { grade: 'C', label: 'Fair', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.35)', glow: '0 0 16px rgba(245, 158, 11, 0.25)' };
  if (score >= 50) return { grade: 'D', label: 'Needs attention', color: '#f97316', bg: 'rgba(249, 115, 22, 0.12)', border: 'rgba(249, 115, 22, 0.35)', glow: '0 0 16px rgba(249, 115, 22, 0.25)' };
  return { grade: 'F', label: 'Critical', color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.12)', border: 'rgba(244, 63, 94, 0.35)', glow: '0 0 16px rgba(244, 63, 94, 0.25)' };
};

const getSubScoreStyle = (key: string, val: number) => {
  switch (key) {
    case 'architecture':
      return {
        bar: 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_12px_rgba(16,185,129,0.35)]',
        text: 'text-emerald-400',
        badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      };
    case 'security':
      return val < 50
        ? {
            bar: 'bg-gradient-to-r from-rose-500 to-red-600 shadow-[0_0_12px_rgba(244,63,94,0.35)]',
            text: 'text-rose-400',
            badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          }
        : {
            bar: 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_12px_rgba(16,185,129,0.35)]',
            text: 'text-emerald-400',
            badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          };
    case 'maintainability':
      return {
        bar: 'bg-gradient-to-r from-indigo-500 to-blue-500 shadow-[0_0_12px_rgba(99,102,241,0.35)]',
        text: 'text-indigo-400',
        badge: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
      };
    case 'coupling':
      return {
        bar: 'bg-gradient-to-r from-amber-500 to-orange-400 shadow-[0_0_12px_rgba(245,158,11,0.35)]',
        text: 'text-amber-400',
        badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      };
    case 'evidence_coverage':
      return {
        bar: 'bg-gradient-to-r from-cyan-400 to-sky-500 shadow-[0_0_12px_rgba(6,182,212,0.35)]',
        text: 'text-cyan-400',
        badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
      };
    default:
      return {
        bar: 'bg-gradient-to-r from-purple-500 to-violet-500 shadow-[0_0_12px_rgba(168,85,247,0.35)]',
        text: 'text-purple-400',
        badge: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      };
  }
};

export const OverviewView: React.FC<OverviewViewProps> = ({ data: propData }) => {
  const storeData = useAppStore(s => s.analysisData);
  const isAnalyzing = useAppStore(s => s.isAnalyzing);
  const analysisError = useAppStore(s => s.analysisError);
  const data = propData ?? storeData;

  if (isAnalyzing) {
    return (
      <div className="space-y-4">
        <div className="dl-flex-gap-3 items-center">
          <span className="dl-panel-label">ANALYZING REPOSITORY</span>
          <span className="dl-caret text-xs font-mono" style={{ color: 'var(--dl-accent)' }}>parsing AST · building graph · running agents · verifying evidence</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="card" />)}
        </div>
        <Skeleton variant="card" />
        <p className="text-xs font-mono" style={{ color: 'var(--dl-text-muted)' }}>
          Large repositories can take several minutes. You can keep browsing — results stream in when ready.
        </p>
      </div>
    );
  }

  if (analysisError) {
    return (
      <GlassPanel className="p-6 text-center" style={{ borderColor: 'var(--semantic-insufficient-border)' }}>
        <AlertTriangle className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--semantic-insufficient)' }} />
        <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-1">Analysis failed</h2>
        <p className="text-xs font-mono" style={{ color: 'var(--semantic-insufficient)' }}>{analysisError}</p>
        <p className="text-xs mt-3" style={{ color: 'var(--dl-text-dim)' }}>
          Check the repository path and that the backend at <span className="font-mono">127.0.0.1:8000</span> is running, then retry from the sidebar.
        </p>
      </GlassPanel>
    );
  }

  if (!data) {
    return (
      <GlassPanel className="p-8 text-center">
        <Layers className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--dl-accent)' }} />
        <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-2">No analysis yet</h2>
        <p className="text-sm max-w-md mx-auto" style={{ color: 'var(--dl-text-dim)' }}>
          Select a repository in the sidebar — <span className="font-mono">GitHub URL</span>, local path, or <span className="font-mono">.zip</span> upload — and click <strong className="text-slate-900 dark:text-white">Analyze Repository</strong> to generate the full intelligence overview.
        </p>
        <div className="mt-4 flex justify-center gap-2">
          <span className="text-[11px] font-mono px-2 py-1 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)', color: 'var(--dl-text-muted)' }}>eval_repos/spring-petclinic</span>
          <span className="text-[11px] font-mono px-2 py-1 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)', color: 'var(--dl-text-muted)' }}>https://github.com/owner/repo</span>
        </div>
      </GlassPanel>
    );
  }

  const score: number | null = data?.repository_intelligence_score?.overall ?? null;
  const subScores: Record<string, number> = data?.repository_intelligence_score?.sub_scores ?? {};
  const explanations: Record<string, string> = data?.repository_intelligence_score?.sub_score_explanations ?? {};
  const timing: Record<string, number> = data?.timing_metrics ?? {};
  const summary: Record<string, any> = data?.repo_summary ?? {};
  const recommendations: any[] = data?.top_engineering_recommendations ?? [];
  const totalFindings = data?.total_verified_findings ?? 0;
  const rejected = data?.total_rejected_findings ?? 0;
  const repoName: string = data?.repository ?? summary.repository ?? '';
  const isEmptyRepo = (data?.parse_stats?.files_parsed ?? summary.total_classes ?? 1) === 0 && Object.keys(subScores).length === 0;

  const grade = gradeFor(score);
  const totalMs = timing.total_execution_ms || 1;
  const stages = [
    { key: 'parse_ast_ms', label: 'AST', sub: 'Parsing', icon: Layers },
    { key: 'graph_build_ms', label: 'GRAPH', sub: 'Knowledge graph', icon: Activity },
    { key: 'multi_agent_scan_ms', label: 'AGENTS', sub: 'Multi-agent scan', icon: Zap },
    { key: 'critic_grounding_verification_ms', label: 'CRITIC', sub: 'Grounding checks', icon: ShieldCheck },
    { key: 'recommendation_synthesis_ms', label: 'SYNTH', sub: 'Synthesis', icon: Shield },
  ];

  const bottleneckKey = useMemo(() => {
    let max = -1;
    let k = '';
    for (const s of stages) {
      const v = timing[s.key] || 0;
      if (v > max) { max = v; k = s.key; }
    }
    return k;
  }, [timing]);

  const weakest = useMemo(() => {
    const entries = Object.entries(subScores);
    if (!entries.length) return null;
    return entries.reduce((a, b) => (a[1] < b[1] ? a : b));
  }, [subScores]);

  const strongest = useMemo(() => {
    const entries = Object.entries(subScores);
    if (!entries.length) return null;
    return entries.reduce((a, b) => (a[1] > b[1] ? a : b));
  }, [subScores]);

  // Heartbeat for empty/unparsable repo
  if (isEmptyRepo || score === null) {
    return (
      <div className="space-y-4">
        <GlassPanel className="p-4 dl-flex-between flex-wrap gap-3">
          <div>
            <div className="dl-flex-gap-2 mb-1">
              {summary.language && <Badge variant="not-verified" size="sm">{summary.language}</Badge>}
              <span className="text-xs font-mono" style={{ color: 'var(--dl-text-dim)' }}>{repoName || 'Repository'}</span>
            </div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Repository Intelligence Overview</h1>
            <p className="text-xs font-mono mt-1" style={{ color: 'var(--semantic-risk-medium)' }}>
              {data?.status_message || 'No parsable source files detected for this input. Try a different path or repository.'}
            </p>
          </div>
          <div className="text-center px-6 py-3 rounded-sm" style={{ background: grade.bg, border: `1px solid ${grade.color}30` }}>
            <div className="text-2xl font-bold" style={{ color: grade.color, fontFamily: 'var(--dl-font-mono)' }}>{grade.grade}</div>
            <div className="text-[10px] font-mono" style={{ color: grade.color }}>{grade.label}</div>
          </div>
        </GlassPanel>
        <GlassPanel className="p-4">
          <span className="dl-panel-label block mb-2">WHAT HAPPENED</span>
          <ul className="text-xs space-y-1.5 list-disc ml-4" style={{ color: 'var(--dl-text-dim)' }}>
            <li>Parser found <strong className="text-slate-900 dark:text-white">{data?.parse_stats?.files_parsed ?? 0}</strong> files, <strong className="text-slate-900 dark:text-white">{data?.stats?.classes_found ?? summary.total_classes ?? 0}</strong> symbols.</li>
            <li>Graph and agents ran but produced no scorable findings — nothing to ground.</li>
            <li>This is expected for empty, binary-only, or unsupported repositories.</li>
          </ul>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header — score + context */}
      <GlassPanel className="p-4 dl-flex-between flex-wrap gap-4">
        <div className="min-w-0 flex-1">
          <div className="dl-flex-gap-2 flex-wrap mb-2">
            {summary.framework && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-sm bg-teal-500/15 text-teal-300 border border-teal-500/30 uppercase">
                {summary.framework}
              </span>
            )}
            {summary.language && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-sm bg-sky-500/15 text-sky-300 border border-sky-500/30 uppercase">
                {summary.language}
              </span>
            )}
            <span className="text-xs font-mono text-slate-400">
              {[summary.repo_type, summary.analysis_scope, repoName].filter(Boolean).join(' · ') || 'Repository'}
            </span>
          </div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Repository Intelligence Overview</h1>
          <p className="text-sm mt-1 max-w-2xl text-slate-300 dark:text-slate-400">
            System-level health grounded in structural evidence — not heuristics. Every score traces to a verified finding or an explicit gap.
          </p>
          {data?.status_message && (
            <p className="text-xs font-mono mt-2" style={{ color: 'var(--semantic-risk-medium)' }}>{data.status_message}</p>
          )}
          {weakest && strongest && (
            <p className="text-xs mt-2 text-slate-400">
              Strongest: <strong className="text-slate-100 capitalize">{weakest[1] > strongest[1] ? weakest[0].replace('_',' ') : strongest[0].replace('_',' ')}</strong> ({Math.max(...Object.values(subScores))}%)
              {' · '} Weakest: <strong className="text-slate-100 capitalize">{weakest[0].replace('_',' ')}</strong> ({weakest[1]}%) — start there.
            </p>
          )}
        </div>

        <div className="flex items-center gap-4 shrink-0">
          {/* Circular gauge */}
          <div className="relative w-24 h-24 flex items-center justify-center shrink-0">
            <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
              <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="8" />
              <circle
                cx="48" cy="48" r="40" fill="none"
                stroke={grade.color} strokeWidth="8" strokeLinecap="round"
                strokeDasharray={`${(Math.max(0, Math.min(100, score ?? 0)) / 100) * 251.2} 251.2`}
                style={{
                  transition: 'stroke-dasharray 600ms cubic-bezier(0.16,1,0.3,1)',
                  filter: `drop-shadow(0 0 6px ${grade.color}88)`
                }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold font-mono" style={{ color: grade.color }}>{score}</span>
              <span className="text-[10px] font-mono -mt-1 text-slate-400">/ 100</span>
            </div>
          </div>
          <div className="text-left">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-sm text-xs font-bold font-mono tracking-wider border"
              style={{ background: grade.bg, color: grade.color, borderColor: grade.border, boxShadow: grade.glow !== 'none' ? grade.glow : undefined }}
            >
              GRADE {grade.grade} · {grade.label.toUpperCase()}
            </div>
            <p className="text-[11px] font-mono mt-2 max-w-[180px] leading-relaxed text-slate-400">
              {score !== null && score >= 80 ? 'Healthy codebase — keep the current layering and keep evidence coverage high.' : score !== null && score >= 60 ? 'Solid, with clear next improvements below.' : 'Needs attention — weakest sub-scores point to the highest-leverage fixes.'}
            </p>
          </div>
        </div>
      </GlassPanel>

      {/* Key Metrics — with honest deltas and vibrant accent cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <GlassPanel className="p-4 border border-rose-500/25 dark:bg-[#11131a] hover:border-rose-500/45 transition-colors shadow-[0_0_12px_rgba(244,63,94,0.06)]">
          <div className="dl-flex-between mb-2">
            <span className="dl-panel-label text-rose-300/90">CRITICAL ISSUES</span>
            <Badge variant="risk-high" size="sm">HIGH</Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${recommendations.filter((r: any) => r.priority === 'HIGH').length > 0 ? 'text-rose-400' : 'text-slate-100'}`}>
              {recommendations.filter((r: any) => r.priority === 'HIGH').length}
            </span>
            <span className="text-[11px] font-mono text-slate-400">/ {recommendations.length} recs</span>
          </div>
          <p className="text-xs mt-1 flex items-center gap-1.5 text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]" />
            {recommendations.filter((r: any) => r.priority === 'HIGH').length === 0 ? 'No critical blockers' : 'Immediate remediation needed'}
          </p>
        </GlassPanel>

        <GlassPanel className="p-4 border border-emerald-500/25 dark:bg-[#11131a] hover:border-emerald-500/45 transition-colors shadow-[0_0_12px_rgba(16,185,129,0.06)]">
          <div className="dl-flex-between mb-2">
            <span className="dl-panel-label text-emerald-300/90">VERIFIED FINDINGS</span>
            <Badge variant="verified" size="sm">VERIFIED</Badge>
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">{totalFindings}</div>
          <p className="text-xs mt-1 flex items-center gap-1.5 text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            {totalFindings === 0 ? 'No grounded findings — clean or unscanned' : 'Grounded in AST + graph evidence'}
          </p>
        </GlassPanel>

        <GlassPanel className="p-4 border border-purple-500/25 dark:bg-[#11131a] hover:border-purple-500/45 transition-colors shadow-[0_0_12px_rgba(168,85,247,0.06)]">
          <div className="dl-flex-between mb-2">
            <span className="dl-panel-label text-purple-300/90">CRITIC REJECTIONS</span>
            <Badge variant="ai-suggestion" size="sm">FILTERED</Badge>
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400">{rejected}</div>
          <p className="text-xs mt-1 flex items-center gap-1.5 text-slate-400">
            <TrendingUp className="w-3.5 h-3.5 text-purple-400" />
            {rejected === 0 ? 'No hallucinations detected' : `${rejected} hallucinated claims removed`}
          </p>
        </GlassPanel>

        <GlassPanel className="p-4 border border-cyan-500/25 dark:bg-[#11131a] hover:border-cyan-500/45 transition-colors shadow-[0_0_12px_rgba(6,182,212,0.06)]">
          <div className="dl-flex-between mb-2">
            <span className="dl-panel-label text-cyan-300/90">EXECUTION TIME</span>
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            {timing.total_execution_ms != null ? `${Math.round(timing.total_execution_ms)}` : '—'}
            <span className="text-sm font-normal text-slate-400">{timing.total_execution_ms != null ? ' ms' : ''}</span>
          </div>
          <p className="text-xs mt-1 text-slate-400">
            {timing.total_execution_ms != null && timing.total_execution_ms > 5000 ? 'Large repo — consider incremental analysis' : '5-stage pipeline end-to-end'}
          </p>
        </GlassPanel>
      </div>

      {/* Sub-scores — advanced, explainable */}
      <GlassPanel className="p-4 border border-zinc-800/80 dark:bg-[#11131a]">
        <div className="dl-flex-between mb-1">
          <span className="dl-panel-label text-slate-200">INTELLIGENCE SUB-SCORES — WHAT DRIVES THE GRADE</span>
          <span className="text-[10px] font-mono flex items-center gap-1 text-slate-400"><Info className="w-3 h-3 text-cyan-400" /> weighted · evidence-grounded</span>
        </div>
        <p className="text-xs mb-4 text-slate-400">
          Architecture 30% · Security 25% · Maintainability 20% · Coupling 15% · Evidence 10%. Each bar shows the score and <em>why</em> — hover for the full formula.
        </p>
        <div className="space-y-3.5">
          {Object.entries(subScores).map(([key, val]) => {
            const exp = explanations[key] || '';
            const style = getSubScoreStyle(key, val);
            return (
              <div key={key} className="group">
                <div className="dl-flex-between mb-1.5">
                  <span className="text-sm font-medium text-slate-200 capitalize flex items-center gap-2">
                    {key.replace(/_/g, ' ')}
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border hidden group-hover:inline-flex ${style.badge}`} title={exp}>
                      {exp.slice(0, 80)}
                    </span>
                  </span>
                  <span className={`text-sm font-bold font-mono ${style.text}`}>{val}%</span>
                </div>
                <div className="w-full h-2.5 rounded-full overflow-hidden flex bg-zinc-200 dark:bg-[#161824] border border-transparent dark:border-zinc-800/80" title={exp}>
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${style.bar}`}
                    style={{ width: `${val}%` }}
                  />
                </div>
                <p className="text-[11px] font-mono mt-1 leading-relaxed hidden group-hover:block text-slate-400">{exp}</p>
              </div>
            );
          })}
        </div>
        {weakest && (weakest[1] as number) < 70 && (
          <div className="mt-4 p-3 rounded flex gap-2.5 bg-amber-500/10 border border-amber-500/30">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
            <p className="text-xs leading-relaxed text-amber-200/90">
              <strong className="capitalize text-amber-300">{weakest[0].replace(/_/g,' ')}</strong> is the weakest link ({weakest[1]}%). {explanations[weakest[0]] || ''} Fixing this moves the overall grade fastest.
            </p>
          </div>
        )}
      </GlassPanel>

      {/* Critic Rejections & Hallucination Defense Shield */}
      {((data?.rejected_findings_sample && data.rejected_findings_sample.length > 0) || rejected > 0) && (
        <GlassPanel className="p-4 space-y-3 border border-purple-500/25 dark:bg-[#11131a] shadow-[0_0_15px_rgba(168,85,247,0.05)]">
          <div className="dl-flex-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-400" />
              <span className="dl-panel-label text-purple-300">CRITIC REJECTIONS & HALLUCINATION DEFENSE</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-300">
                {rejected} CLAIMS BLOCKED
              </span>
              <Badge variant="not-verified" size="sm">FAIL-CLOSED</Badge>
            </div>
          </div>
          <p className="text-xs text-slate-300 dark:text-slate-400 leading-relaxed">
            Every candidate finding produced by scanning agents undergoes mandatory 4-source audit verification against the AST, knowledge graph, Semgrep rules, and file paths. If a claim lacks hard evidence (or was synthetically injected to test rejection), the Critic blocks it from entering documentation, codemaps, and recommendations.
          </p>

          <div className="space-y-2 mt-2">
            {(data?.rejected_findings_sample || []).slice(0, 5).map((rf: any, rfi: number) => {
              const trail = rf.evidence_trail || {};
              return (
                <div key={rfi} className="p-3 rounded border border-zinc-800 bg-[#0e1017] space-y-2">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-slate-100 truncate max-w-md">
                      {rf.title || rf.claim || 'Unverified Candidate Finding'}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-rose-500/40 bg-rose-500/15 text-rose-300 font-bold">
                      REJECTED (FAIL-CLOSED)
                    </span>
                  </div>
                  
                  {/* 4-source verification breakdown */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
                    <div className="p-1.5 rounded border border-zinc-800 bg-[#12141c]">
                      <div className="text-[9px] text-slate-400">KNOWLEDGE GRAPH</div>
                      <div className={`font-bold ${trail.graph_check?.passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {trail.graph_check?.passed ? '✓ PASSED' : '✗ NO EVIDENCE'}
                      </div>
                    </div>
                    <div className="p-1.5 rounded border border-zinc-800 bg-[#12141c]">
                      <div className="text-[9px] text-slate-400">AST STRUCTURE</div>
                      <div className={`font-bold ${trail.ast_check?.passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {trail.ast_check?.passed ? '✓ MATCHED' : '✗ FAIL CLOSED'}
                      </div>
                    </div>
                    <div className="p-1.5 rounded border border-zinc-800 bg-[#12141c]">
                      <div className="text-[9px] text-slate-400">SEMGREP TRUTH</div>
                      <div className={`font-bold ${trail.semgrep_check?.passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {trail.semgrep_check?.passed ? '✓ CONFIRMED' : '✗ UNCONFIRMED'}
                      </div>
                    </div>
                    <div className="p-1.5 rounded border border-zinc-800 bg-[#12141c]">
                      <div className="text-[9px] text-slate-400">STRUCTURAL PATH</div>
                      <div className={`font-bold ${trail.structural_check?.passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {trail.structural_check?.passed ? '✓ PATH MATCH' : '✗ NOT FOUND'}
                      </div>
                    </div>
                  </div>

                  {(trail.ast_check?.details || trail.graph_check?.details) && (
                    <p className="text-[10px] font-mono text-slate-400">
                      Audit note: {trail.ast_check?.details || trail.graph_check?.details}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </GlassPanel>
      )}

      {/* Pipeline — bottleneck-aware */}
      <GlassPanel className="p-4 border border-zinc-800/80 dark:bg-[#11131a]">
        <div className="dl-flex-between mb-3">
          <span className="dl-panel-label text-slate-200">PIPELINE STAGE BREAKDOWN — WHERE TIME GOES</span>
          <span className="text-[10px] font-mono text-slate-400">hover a stage for exact ms</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {stages.map(s => {
            const v = timing[s.key] as number | undefined;
            const pct = v != null && totalMs ? (v / totalMs) * 100 : 0;
            const isBottleneck = s.key === bottleneckKey && pct > 30;
            const Icon = s.icon;
            const stageConfig: Record<string, { color: string; bar: string; icon: string }> = {
              parse_ast_ms: { color: 'text-sky-400', bar: 'bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.4)]', icon: 'text-sky-400' },
              graph_build_ms: { color: 'text-cyan-400', bar: 'bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.4)]', icon: 'text-cyan-400' },
              multi_agent_scan_ms: { color: 'text-purple-400', bar: 'bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.4)]', icon: 'text-purple-400' },
              critic_grounding_verification_ms: { color: 'text-emerald-400', bar: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]', icon: 'text-emerald-400' },
              recommendation_synthesis_ms: { color: 'text-amber-400', bar: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]', icon: 'text-amber-400' },
            };
            const cfg = stageConfig[s.key] || { color: 'text-cyan-400', bar: 'bg-cyan-500', icon: 'text-cyan-400' };
            return (
              <div
                key={s.key}
                className={`p-3 rounded relative overflow-hidden transition-all ${
                  isBottleneck
                    ? 'border border-amber-500/40 bg-amber-500/10 shadow-[0_0_12px_rgba(245,158,11,0.15)]'
                    : 'border border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-[#0e1017] hover:dark:border-zinc-700'
                }`}
                title={`${s.label}: ${v != null ? `${v}ms` : '—'} (${pct.toFixed(1)}%)`}
              >
                <div className="dl-flex-between mb-1">
                  <span className="text-[11px] font-mono font-bold flex items-center gap-1.5 text-zinc-300">
                    <Icon className={`w-3.5 h-3.5 ${cfg.icon}`} />
                    {s.label}
                  </span>
                  {isBottleneck && (
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border border-amber-500/40 bg-amber-500/20 text-amber-300">
                      BOTTLENECK
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold font-mono text-slate-100">{v != null ? `${Math.round(v)}ms` : '—'}</div>
                <div className="text-[10px] font-mono text-slate-400">{s.sub}</div>
                <div className="h-1.5 rounded-full overflow-hidden mt-2 bg-zinc-200 dark:bg-[#181a24] border border-transparent dark:border-zinc-800/60">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isBottleneck ? 'bg-amber-500 dark:bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.5)]' : cfg.bar
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="text-[10px] font-mono mt-1 text-slate-400">{pct.toFixed(1)}%</div>
              </div>
            );
          })}
        </div>
        {timing.total_execution_ms != null && timing.total_execution_ms > 0 && (
          <p className="text-[11px] font-mono mt-3 text-zinc-500 dark:text-zinc-400">
            Total <strong className="text-zinc-900 dark:text-zinc-100 font-mono">{Math.round(timing.total_execution_ms)}ms</strong> end-to-end. Bottleneck is <strong className="text-zinc-900 dark:text-zinc-100">{stages.find(s => s.key === bottleneckKey)?.label || '—'}</strong> — start optimizing there for the biggest win.
          </p>
        )}
      </GlassPanel>

      {/* Composition + Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <GlassPanel className="p-4">
          <div className="dl-flex-between mb-3">
            <span className="dl-panel-label">CODEBASE COMPOSITION</span>
            <span className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>{summary.language || '—'}</span>
          </div>
          <div className="space-y-2.5">
            {[
              ['Total Symbols', summary.total_classes],
              ['Controllers', summary.controllers],
              ['Services', summary.services],
              ['Repositories', summary.repositories],
              ['Entities', summary.entities],
              ['Endpoints', data?.endpoints?.length],
            ].map(([label, val]) => (
              <div key={label as string} className="dl-flex-between">
                <span className="text-sm" style={{ color: 'var(--dl-text)' }}>{label}</span>
                <span className="font-mono text-sm font-semibold" style={{ color: val == null ? 'var(--dl-text-muted)' : 'var(--dl-text-strong)' }}>
                  {val == null ? '—' : String(val)}
                </span>
              </div>
            ))}
          </div>
          <p className="text-[11px] font-mono mt-3" style={{ color: 'var(--dl-text-muted)' }}>
            Stereotypes come from parser evidence — not heuristics. Empty means that layer wasn't detected, not that it doesn't exist.
          </p>
        </GlassPanel>

        <GlassPanel className="p-4">
          <div className="dl-flex-between mb-3">
            <span className="dl-panel-label">TOP RECOMMENDATIONS — GROUNDED, PRIORITIZED</span>
            <span className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>{recommendations.length} total</span>
          </div>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {recommendations.length === 0 ? (
              <div className="text-center py-6">
                <ShieldCheck className="w-6 h-6 mx-auto mb-2" style={{ color: 'var(--semantic-verified)' }} />
                <p className="text-xs font-medium text-slate-900 dark:text-white">No grounded recommendations</p>
                <p className="text-xs mt-1" style={{ color: 'var(--dl-text-muted)' }}>
                  Either the codebase is clean, or the critic filtered everything as unverified. Check <span className="font-mono">Critic Rejections</span> above.
                </p>
              </div>
            ) : recommendations.slice(0, 5).map((rec: any, i: number) => (
              <div key={i} className="p-3 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                <div className="dl-flex-between gap-2 mb-1">
                  <span className="text-sm font-medium text-slate-900 dark:text-white leading-tight flex-1">{rec.title}</span>
                  <Badge variant={`risk-${String(rec.priority || 'medium').toLowerCase()}` as any} size="sm">{rec.priority}</Badge>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--dl-text-dim)' }}>{rec.reason}</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm" style={{ background: 'var(--dl-bg-elevated)', border: '1px solid var(--dl-panel-border)', color: 'var(--dl-text-muted)' }}>{rec.category}</span>
                  {rec.file && <span className="text-[10px] font-mono truncate max-w-[180px]" style={{ color: 'var(--dl-text-muted)' }}>{rec.file}</span>}
                </div>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
    </div>
  );
};
