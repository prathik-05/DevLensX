import React, { useState, useEffect } from 'react';
import { useAppStore } from '../store';
import { useWorkspaceContext } from '../workspaceContext';
import { seedGovernanceDemo } from '../apiClient';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  FileCode2,
  RefreshCw,
  GitCompare,
  ArrowRight,
  Layers,
  Sparkles,
  Boxes,
  HelpCircle,
  Info,
} from 'lucide-react';

interface GovernanceRule {
  rule_id: string;
  name: string;
  rule_type: string;
  severity: string;
  description: string;
  enabled: boolean;
}

interface GovernanceFinding {
  rule_id: string;
  violation_type: string;
  severity: string;
  verdict: string;
  source_symbol: string;
  target_symbol?: string;
  file_path: string;
  line_start: number;
  line_end: number;
  evidence_ref?: any;
  description: string;
  committable_fix?: string;
  requires_user_action: boolean;
}

interface ContractDifference {
  change_type: string;
  is_breaking: boolean;
  endpoint_path: string;
  http_method: string;
  details: string;
  provider_spec?: any;
  consumer_spec?: any;
}

interface ContractReport {
  workspace_id: string;
  producer: { repository_id: string; analysis_run_id: string; commit_hash?: string };
  consumer: { repository_id: string; analysis_run_id: string; commit_hash?: string };
  is_compatible: boolean;
  breaking_count: number;
  non_breaking_count: number;
  differences: ContractDifference[];
}

export const GovernanceView: React.FC = () => {
  const { analysisData } = useAppStore();
  const ws = useWorkspaceContext();
  const [activeTab, setActiveTab] = useState<'rules' | 'contracts'>('rules');

  // Governance state
  const [rules, setRules] = useState<GovernanceRule[]>([]);
  const [findings, setFindings] = useState<GovernanceFinding[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [evalSummary, setEvalSummary] = useState<{
    total: number;
    verified: number;
    suggestion: number;
    insufficient: number;
  } | null>(null);

  // Contracts state
  const [workspaceId, setWorkspaceId] = useState('ws-ecommerce');
  const [producerRepoId, setProducerRepoId] = useState('orders-service');
  const [consumerRepoId, setConsumerRepoId] = useState('gateway-client');
  const [producerRunId, setProducerRunId] = useState('run-prod-v2');
  const [consumerRunId, setConsumerRunId] = useState('run-cons-v1');
  const [verifyingContracts, setVerifyingContracts] = useState(false);
  const [contractReport, setContractReport] = useState<ContractReport | null>(null);
  const [contractError, setContractError] = useState<string | null>(null);

  // Demo state
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoLoaded, setDemoLoaded] = useState(false);

  // Fetch rules on mount
  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setLoadingRules(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/governance/rules');
      if (res.ok) {
        const data = await res.json();
        setRules(data.rules || []);
      }
    } catch (e) {
      console.error('Failed to fetch governance rules:', e);
    } finally {
      setLoadingRules(false);
    }
  };

  const handleSeedDemo = async () => {
    setDemoLoading(true);
    setEvalError(null);
    setContractError(null);
    try {
      const demo = await seedGovernanceDemo();
      setDemoLoaded(true);

      // Pre-fill contracts parameters
      if (demo.contracts_demo) {
        setWorkspaceId(demo.contracts_demo.workspace_id);
        setProducerRepoId(demo.contracts_demo.producer_repo_id);
        setConsumerRepoId(demo.contracts_demo.consumer_repo_id);
        setProducerRunId(demo.contracts_demo.producer_run_id);
        setConsumerRunId(demo.contracts_demo.consumer_run_id);
      }

      // Automatically evaluate demo rules
      if (demo.rules_demo) {
        const evalRes = await fetch('http://127.0.0.1:8000/api/governance/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            analysis_run_id: demo.rules_demo.analysis_run_id,
            repository_id: demo.rules_demo.repository_id,
          }),
        });
        if (evalRes.ok) {
          const evalData = await evalRes.json();
          setFindings(evalData.findings || []);
          setEvalSummary({
            total: evalData.total_findings || 0,
            verified: evalData.verified_count || 0,
            suggestion: evalData.suggestion_count || 0,
            insufficient: evalData.insufficient_evidence_count || 0,
          });
        }
      }

      // Automatically verify contracts
      if (demo.contracts_demo) {
        const cRes = await fetch('http://127.0.0.1:8000/api/governance/contracts/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(demo.contracts_demo),
        });
        if (cRes.ok) {
          const cData = await cRes.json();
          setContractReport(cData.report);
        }
      }
    } catch (e: any) {
      setEvalError(e?.message || 'Failed to seed demo environment');
    } finally {
      setDemoLoading(false);
    }
  };

  const runEvaluation = async () => {
    const runId = ws.analysis_run_id || analysisData?.analysis_run_id || (demoLoaded ? 'run-demo-eshop-001' : null);
    if (!runId) {
      setEvalError('No active analysis snapshot found. Click "Load Live Demo Data" above to test.');
      return;
    }

    setEvaluating(true);
    setEvalError(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/governance/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_run_id: runId,
          repository_id: ws.repository_id || analysisData?.repository || (demoLoaded ? 'demo-eshop-service' : undefined),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setFindings(data.findings || []);
        setEvalSummary({
          total: data.total_findings || 0,
          verified: data.verified_count || 0,
          suggestion: data.suggestion_count || 0,
          insufficient: data.insufficient_evidence_count || 0,
        });
      } else {
        const err = await res.json();
        setEvalError(err.detail || 'Evaluation failed.');
      }
    } catch (e: any) {
      setEvalError(e?.message || 'Evaluation network error');
    } finally {
      setEvaluating(false);
    }
  };

  const runContractVerification = async () => {
    setVerifyingContracts(true);
    setContractError(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/governance/contracts/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspaceId,
          producer_repo_id: producerRepoId,
          consumer_repo_id: consumerRepoId,
          producer_run_id: producerRunId,
          consumer_run_id: consumerRunId,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setContractReport(data.report);
      } else {
        const err = await res.json();
        setContractError(err.detail || 'Contract verification failed');
      }
    } catch (e: any) {
      setContractError(e?.message || 'Network error verifying contracts');
    } finally {
      setVerifyingContracts(false);
    }
  };

  const activeRunDisplay = ws.analysis_run_id || analysisData?.analysis_run_id || (demoLoaded ? 'run-demo-eshop-001 (Demo)' : 'No snapshot active');

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 pb-12">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <ShieldCheck className="w-6 h-6" />
            </span>
            <h1 className="text-2xl font-bold text-slate-100">Living Architectural Governance & Contracts</h1>
            <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">Phase P5</span>
          </div>
          <p className="text-sm text-slate-400 mt-1.5 max-w-3xl">
            Grounded rule validation, cycle detection, and cross-service contract verification strictly enforced through EvidenceResolver and ClaimVerifier.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSeedDemo}
            disabled={demoLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600/90 hover:bg-indigo-600 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${demoLoading ? 'animate-spin' : ''}`} />
            <span>{demoLoading ? 'Loading Demo Data...' : demoLoaded ? 'Demo Loaded ✓' : 'Load Live Demo Data'}</span>
          </button>

          {/* Tab Switcher */}
          <div className="flex items-center bg-zinc-900/90 p-1 rounded-xl border border-zinc-800">
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === 'rules'
                  ? 'bg-zinc-800 text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" />
                <span>Architectural Rules</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('contracts')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === 'contracts'
                  ? 'bg-zinc-800 text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <GitCompare className="w-3.5 h-3.5" />
                <span>Cross-Service Contracts</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: ARCHITECTURAL RULES & EVALUATION */}
      {activeTab === 'rules' && (
        <div className="space-y-6">
          {/* Action Header Card */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-zinc-800 bg-[#11131a]">
            <div>
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold block">Target Snapshot</span>
              <div className="text-sm font-mono font-medium text-slate-200 mt-0.5">
                {activeRunDisplay}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={runEvaluation}
                disabled={evaluating}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
                <span>{evaluating ? 'Evaluating...' : 'Evaluate Governance Rules'}</span>
              </button>
            </div>
          </div>

          {/* Evaluation Error */}
          {evalError && (
            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span>{evalError}</span>
              </div>
              <button
                onClick={handleSeedDemo}
                className="underline hover:text-white font-medium"
              >
                Click to load sample workspace
              </button>
            </div>
          )}

          {/* Summary Cards */}
          {evalSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-zinc-800 bg-[#11131a] space-y-1">
                <div className="text-xs text-slate-400 font-medium">Total Violations</div>
                <div className="text-2xl font-bold font-mono text-slate-100">{evalSummary.total}</div>
              </div>
              <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 space-y-1">
                <div className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Verified (Grounded)</span>
                </div>
                <div className="text-2xl font-bold font-mono text-emerald-400">{evalSummary.verified}</div>
              </div>
              <div className="p-4 rounded-xl border border-blue-500/30 bg-blue-500/10 space-y-1">
                <div className="text-xs text-blue-400 font-medium flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Suggestions</span>
                </div>
                <div className="text-2xl font-bold font-mono text-blue-400">{evalSummary.suggestion}</div>
              </div>
              <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 space-y-1">
                <div className="text-xs text-amber-400 font-medium flex items-center gap-1">
                  <HelpCircle className="w-3.5 h-3.5" />
                  <span>Insufficient Evidence</span>
                </div>
                <div className="text-2xl font-bold font-mono text-amber-400">{evalSummary.insufficient}</div>
              </div>
            </div>
          )}

          {/* Findings List */}
          {findings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                  <span>Evaluation Findings</span>
                  <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-zinc-800 text-slate-300 border border-zinc-700">{findings.length}</span>
                </h2>
              </div>

              <div className="space-y-3">
                {findings.map((f, i) => (
                  <div key={i} className="p-4 rounded-xl border border-zinc-800 bg-[#11131a] space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-zinc-800 text-indigo-300 border border-zinc-700">
                          {f.rule_id}
                        </span>
                        <span className="text-sm font-semibold text-slate-200">{f.source_symbol}</span>
                        {f.target_symbol && (
                          <>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                            <span className="text-sm font-medium text-slate-400">{f.target_symbol}</span>
                          </>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2.5 py-0.5 font-semibold rounded-full border ${
                            f.verdict === 'VERIFIED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : f.verdict === 'AI_SUGGESTION'
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {f.verdict === 'VERIFIED'
                            ? '🟢 VERIFIED'
                            : f.verdict === 'AI_SUGGESTION'
                            ? '🔵 AI SUGGESTION'
                            : '🔴 INSUFFICIENT EVIDENCE'}
                        </span>

                        <span
                          className={`text-xs px-2 py-0.5 font-semibold rounded ${
                            f.severity === 'CRITICAL'
                              ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                              : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {f.severity}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">{f.description}</p>

                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                      <FileCode2 className="w-3.5 h-3.5 text-slate-400" />
                      <span>{f.file_path}#L{f.line_start}-L{f.line_end}</span>
                    </div>

                    {f.committable_fix && (
                      <div className="p-3 rounded-lg bg-zinc-900/80 border border-zinc-800 text-xs space-y-1">
                        <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Suggested Architectural Fix (Requires Developer Approval):</span>
                        </div>
                        <p className="text-slate-400 font-mono">{f.committable_fix}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Rules Catalog */}
          <div className="space-y-4 pt-4 border-t border-zinc-800">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <span>Configured Architectural Rules</span>
                {loadingRules && <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-500" />}
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rules.map(r => (
                <div key={r.rule_id} className="p-4 rounded-xl border border-zinc-800 bg-[#11131a] space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-zinc-800 text-slate-200 border border-zinc-700">
                      {r.rule_id}
                    </span>
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        r.severity === 'CRITICAL'
                          ? 'bg-red-500/10 text-red-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}
                    >
                      {r.severity}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100">{r.name}</h3>
                  <p className="text-xs text-slate-400">{r.description}</p>
                  <div className="pt-2 flex items-center justify-between text-xs text-slate-500 font-mono">
                    <span>Type: {r.rule_type}</span>
                    <span className={r.enabled ? 'text-emerald-400' : 'text-slate-600'}>
                      {r.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CROSS-SERVICE CONTRACTS */}
      {activeTab === 'contracts' && (
        <div className="space-y-6">
          {/* Microservices Setup Card */}
          <div className="p-5 rounded-xl border border-zinc-800 bg-[#11131a] space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <Boxes className="w-5 h-5 text-indigo-400" />
                <span>Multi-Repository Contract Boundaries</span>
              </h2>
              <button
                onClick={handleSeedDemo}
                className="text-xs font-mono text-indigo-400 hover:text-indigo-300 underline"
              >
                Load Microservices Sample
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Federated Workspace ID</label>
                <input
                  type="text"
                  value={workspaceId}
                  onChange={e => setWorkspaceId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-zinc-700 bg-black/60 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Producer Repository ID</label>
                <input
                  type="text"
                  value={producerRepoId}
                  onChange={e => setProducerRepoId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-zinc-700 bg-black/60 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Consumer Repository ID</label>
                <input
                  type="text"
                  value={consumerRepoId}
                  onChange={e => setConsumerRepoId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-zinc-700 bg-black/60 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Producer Analysis Run ID</label>
                <input
                  type="text"
                  value={producerRunId}
                  onChange={e => setProducerRunId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-zinc-700 bg-black/60 text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Consumer Analysis Run ID</label>
                <input
                  type="text"
                  value={consumerRunId}
                  onChange={e => setConsumerRunId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-zinc-700 bg-black/60 text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={runContractVerification}
                disabled={verifyingContracts || !workspaceId || !producerRunId || !consumerRunId}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${verifyingContracts ? 'animate-spin' : ''}`} />
                <span>{verifyingContracts ? 'Verifying Contracts...' : 'Verify Cross-Service Contracts'}</span>
              </button>
            </div>
          </div>

          {/* Contract Error */}
          {contractError && (
            <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{contractError}</span>
              </div>
              <button
                onClick={handleSeedDemo}
                className="underline hover:text-white font-medium"
              >
                Load Microservices Sample Data
              </button>
            </div>
          )}

          {/* Contract Report */}
          {contractReport && (
            <div className="space-y-6">
              <div
                className={`p-5 rounded-xl border ${
                  contractReport.is_compatible
                    ? 'border-emerald-500/40 bg-emerald-500/10'
                    : 'border-red-500/40 bg-red-500/10'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {contractReport.is_compatible ? (
                      <CheckCircle2 className="w-7 h-7 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <AlertTriangle className="w-7 h-7 text-red-400 flex-shrink-0" />
                    )}
                    <div>
                      <h3 className="text-base font-bold text-slate-100">
                        {contractReport.is_compatible
                          ? 'Contracts Compatible — No Breaking Changes'
                          : 'Breaking Contract Violations Detected'}
                      </h3>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {contractReport.producer.repository_id} &rarr; {contractReport.consumer.repository_id}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono font-semibold">
                    <span className="px-2.5 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                      {contractReport.breaking_count} Breaking
                    </span>
                    <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      {contractReport.non_breaking_count} Non-Breaking
                    </span>
                  </div>
                </div>
              </div>

              {/* Differences List */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-200">Contract Differences</h3>
                {contractReport.differences.length === 0 ? (
                  <div className="p-4 rounded-xl border border-zinc-800 bg-[#11131a] text-center text-xs text-slate-400">
                    All consumer expectations match producer endpoints exactly.
                  </div>
                ) : (
                  contractReport.differences.map((diff, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-xl border bg-[#11131a] space-y-2.5 ${
                        diff.is_breaking ? 'border-red-500/40' : 'border-zinc-800'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-zinc-800 text-slate-200 border border-zinc-700">
                            {diff.http_method}
                          </span>
                          <span className="text-xs font-mono font-semibold text-slate-200">{diff.endpoint_path}</span>
                        </div>
                        <span
                          className={`text-xs px-2.5 py-0.5 font-bold rounded-full border ${
                            diff.is_breaking
                              ? 'bg-red-500/15 text-red-400 border-red-500/30'
                              : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          }`}
                        >
                          {diff.is_breaking ? '🚨 BREAKING' : 'COMPATIBLE'}
                        </span>
                      </div>

                      <div className="text-xs font-mono text-indigo-400 font-semibold">{diff.change_type}</div>
                      <p className="text-xs text-slate-300 leading-relaxed">{diff.details}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default GovernanceView;
