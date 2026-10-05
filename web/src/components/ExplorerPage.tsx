import React, { useState, useEffect, useMemo } from 'react';
import type { AnalysisResponse, FileSummaryResponse } from '../types';
import { fetchFileSummary, explainExplorerSymbol } from '../apiClient';
import {
  Folder,
  FileCode,
  ArrowRight,
  Code2,
  Globe,
  Sparkles,
  HelpCircle,
  CornerDownRight,
  Box,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  Search,
  Terminal,
  Loader2,
  Copy,
  Check
} from 'lucide-react';

interface ExplorerPageProps {
  data: AnalysisResponse;
  onNavigateTab?: (tab: string, query?: string) => void;
}

interface AIExplanationResult {
  symbol_name: string;
  file_path: string;
  line_start: number;
  line_end: number;
  stereotype: string;
  action: string;
  explanation: string;
  incoming_callers: Array<{ caller: string; relation?: string }>;
  outgoing_dependencies: Array<{ dependency: string; relation?: string }>;
  blast_radius: string[];
  source_snippet: string;
  citations: string[];
  verdict: string;
}

const AI_ACTIONS = [
  { id: 'what_does_this_do', label: 'What does this do?', icon: HelpCircle, color: '#0284c7' },
  { id: 'why_does_this_exist', label: 'Why does this exist?', icon: Cpu, color: '#4f46e5' },
  { id: 'who_calls_this', label: 'Who calls this?', icon: CornerDownRight, color: '#059669' },
  { id: 'what_does_this_depend_on', label: 'What does this depend on?', icon: Box, color: '#d97706' },
  { id: 'what_would_be_affected', label: 'What would be affected?', icon: AlertTriangle, color: '#dc2626' },
  { id: 'explain_code_simple', label: 'Explain in simple terms', icon: Sparkles, color: '#7c3aed' },
];

export const ExplorerPage: React.FC<ExplorerPageProps> = ({ data, onNavigateTab }) => {
  const nodes = data.knowledge_graph?.nodes || [];
  const repoName = data.repository || 'analyzed-repository';
  const rawClasses = data.classes || [];

  const detectedLang = (data.repo_summary?.language || '').toLowerCase();
  const langExtMap: Record<string, string> = {
    java: '.java',
    python: '.py',
    typescript: '.ts',
    javascript: '.js',
    go: '.go',
    rust: '.rs',
    'c#': '.cs',
    'c++': '.cpp',
  };
  const defaultExt = langExtMap[detectedLang] || '.java';
  const langLabel = data.repo_summary?.language || 'Source';

  const initialFile = nodes[0]?.file || rawClasses[0]?.file || (data.repo_summary.language === 'Python' ? 'main.py' : 'index.ts');
  const [selectedFile, setSelectedFile] = useState<string>(initialFile);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [summary, setSummary] = useState<FileSummaryResponse | null>(null);

  // AI Exploration State
  const [selectedAction, setSelectedAction] = useState<string>('what_does_this_do');
  const [explanation, setExplanation] = useState<AIExplanationResult | null>(null);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [copiedCitation, setCopiedCitation] = useState<string | null>(null);

  useEffect(() => {
    async function loadSummary() {
      if (!selectedFile) return;
      const res = await fetchFileSummary(selectedFile);
      setSummary(res);
    }
    loadSummary();
  }, [selectedFile]);

  // Trigger AI explanation when file or action changes
  const runExplanation = async (actionId: string, fileToExplain: string = selectedFile) => {
    if (!fileToExplain) return;
    setIsExplaining(true);
    setExplainError(null);
    setSelectedAction(actionId);
    try {
      const res = await explainExplorerSymbol(fileToExplain, actionId, data.analysis_run_id);
      if (res && res.status === 'success') {
        setExplanation(res);
      } else {
        setExplainError(res?.detail || 'Could not retrieve AI explanation.');
      }
    } catch (err: any) {
      setExplainError(err.message || 'AI explanation request failed.');
    } finally {
      setIsExplaining(false);
    }
  };

  // Group files dynamically
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes;
    const q = searchQuery.toLowerCase();
    return nodes.filter(n =>
      n.name.toLowerCase().includes(q) ||
      (n.file && n.file.toLowerCase().includes(q)) ||
      (n.package && n.package.toLowerCase().includes(q))
    );
  }, [nodes, searchQuery]);

  const controllers = filteredNodes.filter(
    n => n.stereotype === 'Controller' || n.name.toLowerCase().includes('controller') || n.name.toLowerCase().includes('router') || n.name.toLowerCase().includes('api')
  );
  const services = filteredNodes.filter(
    n => n.stereotype === 'Service' || n.name.toLowerCase().includes('service') || n.name.toLowerCase().includes('handler') || n.name.toLowerCase().includes('manager')
  );
  const repositories = filteredNodes.filter(
    n => n.stereotype === 'Repository' || n.stereotype === 'Entity' || n.name.toLowerCase().includes('repo') || n.name.toLowerCase().includes('db') || n.name.toLowerCase().includes('model')
  );
  const others = filteredNodes.filter(
    n => !controllers.includes(n) && !services.includes(n) && !repositories.includes(n)
  );

  const baseFileName = selectedFile.split('/').pop() || selectedFile;
  const activeClass = rawClasses.find((c: any) => c.file === selectedFile || c.name === baseFileName.split('.')[0]);

  // Code preview lines
  const codeLines = useMemo(() => {
    if (activeClass) {
      return [
        `// Component: ${activeClass.name}`,
        `// Stereotype: ${activeClass.stereotype || 'Component'}`,
        `// Package / Path: ${activeClass.package || activeClass.file}`,
        '',
        `public class ${activeClass.name} {`,
        `    // Injected Dependencies: ${activeClass.injected_dependencies?.join(', ') || 'None'}`,
        ...(activeClass.methods || []).map((m: any) => `    public ${m.return_type || 'void'} ${m.name}() { /* Executed in runtime context */ }`),
        `}`
      ];
    }
    return [
      `# Module: ${baseFileName}`,
      `# Repository: ${repoName}`,
      '',
      `def main():`,
      `    # Primary entrypoint for ` + repoName,
      `    print("Executing ${baseFileName}...")`,
      '',
      `if __name__ == '__main__':`,
      `    main()`
    ];
  }, [activeClass, baseFileName, repoName]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCitation(text);
    setTimeout(() => setCopiedCitation(null), 2000);
  };

  return (
    <div className="space-y-6 font-sans bg-white dark:bg-[#0a0a0f] text-black dark:text-[#f8fafc]">
      {/* Workspace Header */}
      <div className="border-b-2 border-black dark:border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-sky-100 text-sky-900 dark:bg-sky-950/60 dark:text-sky-300 border-2 border-black dark:border-sky-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              AI REPOSITORY EXPLORER
            </span>
            <span className="px-2.5 py-1 text-[11px] font-sans font-black bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-2 border-black dark:border-emerald-500 uppercase tracking-wider shadow-[2px_2px_0px_0px_#000000]">
              ● GROUNDED AST
            </span>
          </div>
          <h1 className="text-2xl font-black text-black dark:text-white flex items-center space-x-2 tracking-tight">
            <Globe className="w-6 h-6 text-[#0284c7]" />
            <span>Interactive Codebase Explorer & AI Inspector</span>
          </h1>
          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium mt-1">
            Browse repository structure, inspect AST method declarations, and interactively question components with grounded Kùzu facts.
          </p>
        </div>

        <div className="flex items-center space-x-2 font-mono text-xs">
          <span className="px-3 py-1.5 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-700 text-black dark:text-white font-bold shadow-[2px_2px_0px_0px_#000000]">
            📦 {nodes.length} Components Synced
          </span>
        </div>
      </div>

      {/* Main 3-Column Layout: Tree (3 cols) | Code Viewer (5 cols) | AI Inspector (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Col 1: File Tree & Filter */}
        <div className="lg:col-span-3 border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-3.5 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none select-none">
          <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2 text-xs font-sans text-black dark:text-white uppercase tracking-wider font-black">
            <span>Files & Modules</span>
            <span className="text-slate-600 dark:text-slate-400 font-bold">{filteredNodes.length} items</span>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-4 h-4 text-black dark:text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-2.5 py-1.5 text-xs bg-white dark:bg-[#070b14] border-2 border-black dark:border-slate-700 text-black dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0284c7] font-medium"
            />
          </div>

          {/* Tree items */}
          <div className="space-y-3 font-mono text-xs max-h-[560px] overflow-y-auto pr-1">
            {controllers.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[#0284c7] font-black py-0.5 font-sans">
                  <Folder className="w-4 h-4" />
                  <span>Controllers ({controllers.length})</span>
                </div>
                <div className="pl-2 space-y-1 border-l-2 border-slate-200 dark:border-slate-800 ml-1.5">
                  {controllers.map(c => {
                    const fname = c.file || `${c.name}${defaultExt}`;
                    const isSel = selectedFile === fname;
                    return (
                      <button
                        key={c.id}
                        onClick={() => {
                          setSelectedFile(fname);
                          setExplanation(null);
                        }}
                        className={`w-full text-left py-1.5 px-2 rounded-none truncate flex items-center space-x-1.5 transition-all text-xs ${
                          isSel
                            ? 'bg-sky-100 dark:bg-sky-950/60 text-black dark:text-sky-300 border-2 border-black dark:border-sky-500 font-bold shadow-[2px_2px_0px_0px_#000000]'
                            : 'text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium'
                        }`}
                      >
                        <FileCode className="w-3.5 h-3.5 shrink-0 text-[#0284c7]" />
                        <span className="truncate">{c.file ? c.file.split('/').pop() : `${c.name}${defaultExt}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {services.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[#059669] font-black py-0.5 font-sans">
                  <Folder className="w-4 h-4" />
                  <span>Services ({services.length})</span>
                </div>
                <div className="pl-2 space-y-1 border-l-2 border-slate-200 dark:border-slate-800 ml-1.5">
                  {services.map(s => {
                    const fname = s.file || `${s.name}${defaultExt}`;
                    const isSel = selectedFile === fname;
                    return (
                      <button
                        key={s.id}
                        onClick={() => {
                          setSelectedFile(fname);
                          setExplanation(null);
                        }}
                        className={`w-full text-left py-1.5 px-2 rounded-none truncate flex items-center space-x-1.5 transition-all text-xs ${
                          isSel
                            ? 'bg-emerald-100 dark:bg-emerald-950/60 text-black dark:text-emerald-300 border-2 border-black dark:border-emerald-500 font-bold shadow-[2px_2px_0px_0px_#000000]'
                            : 'text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium'
                        }`}
                      >
                        <FileCode className="w-3.5 h-3.5 shrink-0 text-[#059669]" />
                        <span className="truncate">{s.file ? s.file.split('/').pop() : `${s.name}${defaultExt}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {repositories.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[#7c3aed] font-black py-0.5 font-sans">
                  <Folder className="w-4 h-4" />
                  <span>Repositories ({repositories.length})</span>
                </div>
                <div className="pl-2 space-y-1 border-l-2 border-slate-200 dark:border-slate-800 ml-1.5">
                  {repositories.map(r => {
                    const fname = r.file || `${r.name}${defaultExt}`;
                    const isSel = selectedFile === fname;
                    return (
                      <button
                        key={r.id}
                        onClick={() => {
                          setSelectedFile(fname);
                          setExplanation(null);
                        }}
                        className={`w-full text-left py-1.5 px-2 rounded-none truncate flex items-center space-x-1.5 transition-all text-xs ${
                          isSel
                            ? 'bg-purple-100 dark:bg-purple-950/60 text-black dark:text-purple-300 border-2 border-black dark:border-purple-500 font-bold shadow-[2px_2px_0px_0px_#000000]'
                            : 'text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium'
                        }`}
                      >
                        <FileCode className="w-3.5 h-3.5 shrink-0 text-[#7c3aed]" />
                        <span className="truncate">{r.file ? r.file.split('/').pop() : `${r.name}${defaultExt}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {others.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-black dark:text-white font-black py-0.5 font-sans">
                  <Folder className="w-4 h-4" />
                  <span>Other Modules ({others.length})</span>
                </div>
                <div className="pl-2 space-y-1 border-l-2 border-slate-200 dark:border-slate-800 ml-1.5">
                  {others.map(o => {
                    const fname = o.file || `${o.name}${defaultExt}`;
                    const isSel = selectedFile === fname;
                    return (
                      <button
                        key={o.id}
                        onClick={() => {
                          setSelectedFile(fname);
                          setExplanation(null);
                        }}
                        className={`w-full text-left py-1.5 px-2 rounded-none truncate flex items-center space-x-1.5 transition-all text-xs ${
                          isSel
                            ? 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white border-2 border-black font-bold'
                            : 'text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium'
                        }`}
                      >
                        <FileCode className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                        <span className="truncate">{o.file ? o.file.split('/').pop() : `${o.name}${defaultExt}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Col 2: Code Viewer & Metrics */}
        <div className="lg:col-span-5 space-y-4">
          {/* Metadata Card */}
          <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-4 space-y-3 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
            <div className="flex flex-wrap items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2.5 gap-2 font-sans text-xs">
              <div className="flex items-center space-x-2">
                <FileCode className="w-5 h-5 text-[#0284c7]" />
                <span className="text-black dark:text-white font-black text-sm">{baseFileName}</span>
                <span className="px-2 py-0.5 bg-sky-100 text-sky-950 dark:bg-sky-950/60 dark:text-sky-300 border border-black dark:border-sky-500 font-bold text-[10px] uppercase">
                  {summary?.stereotype || activeClass?.stereotype || 'Component'}
                </span>
              </div>

              <button
                onClick={() => onNavigateTab && onNavigateTab('copilot', `Explain the internal method implementations and architectural responsibilities of file ${baseFileName}.`)}
                className="px-3 py-1 bg-black hover:bg-slate-800 text-white font-bold flex items-center space-x-1 transition-all text-xs shadow-[2px_2px_0px_0px_#000000]"
              >
                <span>Ask Copilot</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 font-mono text-xs">
              <div className="p-2.5 bg-slate-50 dark:bg-[#070b14] border-2 border-black dark:border-slate-800 space-y-0.5">
                <span className="text-slate-600 dark:text-slate-400 text-[10px] uppercase font-bold block">AST Stereotype</span>
                <span className="text-[#0284c7] font-black truncate block">{summary?.stereotype || activeClass?.stereotype || 'Component'}</span>
              </div>
              <div className="p-2.5 bg-slate-50 dark:bg-[#070b14] border-2 border-black dark:border-slate-800 space-y-0.5">
                <span className="text-slate-600 dark:text-slate-400 text-[10px] uppercase font-bold block">Callers</span>
                <span className="text-[#059669] font-black block">{summary?.used_by_count ?? (explanation?.incoming_callers?.length || 0)} Inbound</span>
              </div>
              <div className="p-2.5 bg-slate-50 dark:bg-[#070b14] border-2 border-black dark:border-slate-800 space-y-0.5">
                <span className="text-slate-600 dark:text-slate-400 text-[10px] uppercase font-bold block">Risk Level</span>
                <span className="text-[#d97706] font-black block">{summary?.risks || 'Standard'}</span>
              </div>
            </div>
          </div>

          {/* Source Code View */}
          <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] overflow-hidden shadow-[3px_3px_0px_0px_#000000] dark:shadow-none font-mono text-xs">
            <div className="bg-slate-100 dark:bg-[#181824] border-b-2 border-black dark:border-slate-800 px-3 py-2 flex items-center justify-between text-xs text-black dark:text-white font-bold">
              <span className="flex items-center space-x-2 truncate">
                <Code2 className="w-4 h-4 text-[#0284c7]" />
                <span className="truncate">{selectedFile}</span>
              </span>
              <span className="text-slate-600 dark:text-slate-400 font-mono text-[11px]">{langLabel} · {codeLines.length} Lines</span>
            </div>

            <div className="p-3.5 overflow-x-auto max-h-[440px] overflow-y-auto space-y-0.5 bg-slate-50 dark:bg-[#070b14]">
              {codeLines.map((line, lIdx) => (
                <div key={lIdx} className="flex items-center space-x-3 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 px-1 transition-colors">
                  <span className="w-6 text-right text-slate-400 select-none text-[10px]">{lIdx + 1}</span>
                  <span className="text-slate-900 dark:text-[#f8fafc] whitespace-pre font-medium">{line}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Col 3: AI Exploration & Question Actions */}
        <div className="lg:col-span-4 space-y-4">
          <div className="border-2 border-black dark:border-slate-800 bg-white dark:bg-[#12131a] p-4 space-y-4 shadow-[3px_3px_0px_0px_#000000] dark:shadow-none">
            <div className="flex items-center justify-between border-b-2 border-black dark:border-slate-800 pb-2">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-[#0284c7]" />
                <span className="font-black text-xs font-sans text-black dark:text-white uppercase tracking-wider">
                  AI Explorer Questions
                </span>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border border-black dark:border-emerald-500">
                LIVE
              </span>
            </div>

            {/* Question Quick-Action Buttons */}
            <div className="grid grid-cols-2 gap-2">
              {AI_ACTIONS.map(action => {
                const Icon = action.icon;
                const isSelected = selectedAction === action.id;
                return (
                  <button
                    key={action.id}
                    onClick={() => runExplanation(action.id)}
                    disabled={isExplaining}
                    className={`p-2.5 rounded-none text-left font-sans text-xs flex items-start space-x-2 transition-all border-2 ${
                      isSelected
                        ? 'bg-sky-100 dark:bg-sky-950/60 border-black dark:border-sky-400 text-black dark:text-sky-200 font-black shadow-[2px_2px_0px_0px_#000000]'
                        : 'bg-white dark:bg-[#181824] border-black dark:border-slate-800 text-black dark:text-slate-200 hover:bg-slate-100 font-bold shadow-[2px_2px_0px_0px_#000000]'
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 shrink-0" style={{ color: action.color }} />
                    <span className="leading-snug text-black dark:text-white">{action.label}</span>
                  </button>
                );
              })}
            </div>

            {/* AI Explanation Result Box */}
            <div className="border-2 border-black dark:border-slate-800 bg-slate-50 dark:bg-[#070b14] p-3.5 space-y-3 min-h-[220px]">
              <div className="flex items-center justify-between border-b-2 border-black/20 dark:border-slate-800 pb-2 text-xs font-sans">
                <span className="text-black dark:text-white font-black flex items-center space-x-1.5 uppercase tracking-wider text-[11px]">
                  <Terminal className="w-3.5 h-3.5 text-[#0284c7]" />
                  <span>AI Inspector Result</span>
                </span>
                {explanation && (
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border border-black dark:border-emerald-500 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{explanation.verdict}</span>
                  </span>
                )}
              </div>

              {isExplaining ? (
                <div className="py-8 flex flex-col items-center justify-center space-y-2 font-mono text-xs text-slate-700 dark:text-slate-300">
                  <Loader2 className="w-6 h-6 animate-spin text-[#0284c7]" />
                  <span className="font-bold">Reasoning over codebase graph & AST...</span>
                </div>
              ) : explainError ? (
                <div className="p-3 bg-red-100 border-2 border-red-500 text-xs text-red-900 font-mono font-bold">
                  {explainError}
                </div>
              ) : explanation ? (
                <div className="space-y-3 font-mono text-xs">
                  {/* Narrative Text */}
                  <div className="text-black dark:text-slate-100 leading-relaxed font-sans text-xs bg-white dark:bg-[#12131a] p-3 border-2 border-black dark:border-slate-800 font-medium">
                    {explanation.explanation}
                  </div>

                  {/* Grounded Source Citation */}
                  {explanation.citations && explanation.citations.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-700 dark:text-slate-300 uppercase font-black block font-sans">
                        AST Source Grounding:
                      </span>
                      <div className="space-y-1">
                        {explanation.citations.map((c, i) => (
                          <div key={i} className="flex items-center justify-between p-2 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-800 text-[11px] font-bold">
                            <span className="text-[#0284c7] truncate">{c}</span>
                            <button
                              onClick={() => copyToClipboard(c)}
                              className="text-black dark:text-white hover:text-slate-600 ml-2"
                              title="Copy citation"
                            >
                              {copiedCitation === c ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Incoming Callers */}
                  {explanation.incoming_callers && explanation.incoming_callers.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-700 dark:text-slate-300 uppercase font-black block font-sans">
                        Incoming Callers ({explanation.incoming_callers.length}):
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {explanation.incoming_callers.map((c, i) => (
                          <span key={i} className="px-2 py-0.5 bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border border-black dark:border-emerald-500 text-[11px] font-bold">
                            {c.caller}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Outgoing Dependencies */}
                  {explanation.outgoing_dependencies && explanation.outgoing_dependencies.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-700 dark:text-slate-300 uppercase font-black block font-sans">
                        Dependencies ({explanation.outgoing_dependencies.length}):
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {explanation.outgoing_dependencies.map((d, i) => (
                          <span key={i} className="px-2 py-0.5 bg-purple-100 text-purple-900 dark:bg-purple-950/60 dark:text-purple-300 border border-black dark:border-purple-500 text-[11px] font-bold">
                            {d.dependency}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Blast Radius */}
                  {explanation.blast_radius && explanation.blast_radius.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-700 dark:text-slate-300 uppercase font-black block font-sans">
                        Downstream Blast Radius:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {explanation.blast_radius.map((b, i) => (
                          <span key={i} className="px-2 py-0.5 bg-red-100 text-red-900 dark:bg-red-950/60 dark:text-red-300 border border-black dark:border-red-500 text-[11px] font-bold">
                            {b}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-slate-700 dark:text-slate-300 font-sans text-xs space-y-2 font-medium">
                  <Sparkles className="w-5 h-5 mx-auto text-[#0284c7]" />
                  <p>Click any AI Explorer question above to analyze <strong className="text-black dark:text-white font-bold">{baseFileName}</strong>.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
