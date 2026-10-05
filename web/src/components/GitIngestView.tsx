import React, { useState, useEffect } from 'react';
import { useAppStore } from '../store';
import {
  fetchGitIngestDigest,
  type GitIngestDigestResponse,
} from '../apiClient';
import {
  FileText,
  FolderTree,
  Cpu,
  Copy,
  Check,
  Download,
  Terminal,
  Filter,
  RefreshCw,
  Code2,
  HardDrive,
} from 'lucide-react';
import { GlassPanel } from './GlassPanel';

export const GitIngestView: React.FC = () => {
  const { repoPath } = useAppStore();
  const [source, setSource] = useState(repoPath || 'd:/projects/DevLensX');
  const [includePatterns, setIncludePatterns] = useState('');
  const [excludePatterns, setExcludePatterns] = useState('node_modules/*,.git/*,dist/*,build/*,*.pyc');
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [digestData, setDigestData] = useState<GitIngestDigestResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'digest' | 'tree' | 'files'>('digest');
  const [filterFileQuery, setFilterFileQuery] = useState('');

  // Update source if repoPath changes and user hasn't edited
  useEffect(() => {
    if (repoPath && (!source || source === 'd:/projects/DevLensX')) {
      setSource(repoPath);
    }
  }, [repoPath]);

  const handleIngest = async () => {
    if (!source.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGitIngestDigest({
        source: source.trim(),
        include_patterns: includePatterns.trim() || undefined,
        exclude_patterns: excludePatterns.trim() || undefined,
      });
      setDigestData(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to extract codebase digest');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!digestData?.prompt_digest) return;
    navigator.clipboard.writeText(digestData.prompt_digest);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!digestData?.prompt_digest) return;
    const blob = new Blob([digestData.prompt_digest], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `codebase_digest_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner / Explainer */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-900/20 via-indigo-900/15 to-emerald-900/20 border border-zinc-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Code2 className="w-6 h-6" />
              </span>
              <h2 className="text-xl font-bold text-slate-100">GitIngest Context & Prompt Bundler</h2>
              <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">Fast LLM Ingest</span>
            </div>
            <p className="text-sm text-slate-400">
              Converts any Git repository URL or local directory into a structured, unified text digest optimized for Large Language Models.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setSource('C:\\Users\\SVCS\\Desktop\\gitingest-main');
              }}
              className="px-3 py-1.5 text-xs font-mono rounded-lg bg-zinc-900/80 border border-zinc-700 text-slate-300 hover:text-white hover:border-indigo-500 transition-colors"
            >
              gitingest-main
            </button>
            <button
              onClick={() => {
                setSource(repoPath || 'd:/projects/DevLensX');
              }}
              className="px-3 py-1.5 text-xs font-mono rounded-lg bg-zinc-900/80 border border-zinc-700 text-slate-300 hover:text-white hover:border-indigo-500 transition-colors"
            >
              DevLensX
            </button>
          </div>
        </div>

        {/* Input Bar */}
        <div className="space-y-3 pt-2">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 font-mono text-xs">
                DIR / URL
              </div>
              <input
                type="text"
                value={source}
                onChange={e => setSource(e.target.value)}
                placeholder="Enter Git repo URL (e.g. https://github.com/...) or local directory path..."
                className="w-full pl-24 pr-4 py-2.5 bg-black/60 border border-zinc-700 rounded-xl text-slate-100 text-sm font-mono focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowFilters(s => !s)}
                className={`px-3 py-2.5 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  showFilters
                    ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                    : 'bg-zinc-900/80 border-zinc-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Filters</span>
              </button>

              <button
                onClick={handleIngest}
                disabled={loading || !source.trim()}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                <span>{loading ? 'Bundling...' : 'Generate Digest'}</span>
              </button>
            </div>
          </div>

          {/* Collapsible Filter Row */}
          {showFilters && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 rounded-xl bg-black/40 border border-zinc-800 text-xs">
              <div>
                <label className="text-slate-400 font-mono block mb-1">Include Patterns (comma-separated):</label>
                <input
                  type="text"
                  value={includePatterns}
                  onChange={e => setIncludePatterns(e.target.value)}
                  placeholder="e.g. *.py, *.ts, src/*"
                  className="w-full px-3 py-1.5 bg-zinc-900/90 border border-zinc-700/80 rounded-lg text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-400 font-mono block mb-1">Exclude Patterns (comma-separated):</label>
                <input
                  type="text"
                  value={excludePatterns}
                  onChange={e => setExcludePatterns(e.target.value)}
                  placeholder="e.g. tests/*, *.log, node_modules/*"
                  className="w-full px-3 py-1.5 bg-zinc-900/90 border border-zinc-700/80 rounded-lg text-slate-200 font-mono"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-center gap-2">
          <span>{error}</span>
        </div>
      )}

      {/* Results View */}
      {digestData && (
        <div className="space-y-6">
          {/* Statistics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                <span>Files Extracted</span>
              </div>
              <div className="text-2xl font-bold text-slate-100 font-mono">
                {digestData.stats.files_analyzed}
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
                <span>Digest Size</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {digestData.stats.total_size_formatted}
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-amber-400" />
                <span>Estimated Tokens</span>
              </div>
              <div className="text-2xl font-bold text-amber-400 font-mono">
                {digestData.stats.estimated_tokens_formatted}
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <FolderTree className="w-3.5 h-3.5 text-purple-400" />
                <span>Format</span>
              </div>
              <div className="text-lg font-bold text-purple-300 font-mono mt-0.5">
                LLM-Optimized
              </div>
            </GlassPanel>
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('digest')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'digest'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white bg-zinc-800/50'
                }`}
              >
                Unified Prompt Digest
              </button>
              <button
                onClick={() => setActiveTab('tree')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'tree'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white bg-zinc-800/50'
                }`}
              >
                Directory Tree
              </button>
              <button
                onClick={() => setActiveTab('files')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'files'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white bg-zinc-800/50'
                }`}
              >
                File Contents
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied Prompt!' : 'Copy for LLM'}</span>
              </button>

              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-slate-200 text-xs font-semibold border border-zinc-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download .txt</span>
              </button>
            </div>
          </div>

          {/* Tab 1: Digest */}
          {activeTab === 'digest' && (
            <div className="relative rounded-2xl border border-zinc-800 bg-[#0d0f14] overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800/80 bg-zinc-950/60 text-xs font-mono text-slate-400">
                <span>Prompt Digest (Ready to paste into Claude, GPT-4, or Gemini)</span>
                <span>{digestData.prompt_digest.length.toLocaleString()} characters</span>
              </div>
              <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto max-h-[600px] leading-relaxed whitespace-pre select-all">
                {digestData.prompt_digest}
              </pre>
            </div>
          )}

          {/* Tab 2: Directory Tree */}
          {activeTab === 'tree' && (
            <div className="rounded-2xl border border-zinc-800 bg-[#0d0f14] overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800/80 bg-zinc-950/60 text-xs font-mono text-slate-400">
                <span>Directory Hierarchy Tree</span>
              </div>
              <pre className="p-4 text-xs font-mono text-emerald-400/90 overflow-x-auto max-h-[600px] leading-relaxed whitespace-pre">
                {digestData.tree}
              </pre>
            </div>
          )}

          {/* Tab 3: File Contents */}
          {activeTab === 'files' && (
            <div className="space-y-3">
              <div className="relative">
                <input
                  type="text"
                  value={filterFileQuery}
                  onChange={e => setFilterFileQuery(e.target.value)}
                  placeholder="Filter by file name or extension..."
                  className="w-full px-4 py-2 bg-black/50 border border-zinc-800 rounded-xl text-xs font-mono text-slate-200"
                />
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-[#0d0f14] overflow-hidden">
                <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto max-h-[600px] leading-relaxed whitespace-pre">
                  {filterFileQuery
                    ? digestData.content
                        .split('================================================')
                        .filter(chunk => chunk.toLowerCase().includes(filterFileQuery.toLowerCase()))
                        .join('================================================')
                    : digestData.content}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* CLI Usage Guide Helper Card */}
      <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#11131a]/60 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span>DevLensX GitIngest Shell CLI Command</span>
        </div>
        <p className="text-xs text-slate-400">
          You can also run this directly as a shell CLI tool to bundle any repository or local folder from terminal:
        </p>
        <div className="p-3 rounded-lg bg-black/70 border border-zinc-800 font-mono text-xs text-slate-300 flex items-center justify-between overflow-x-auto">
          <code>python run_devlensx.py ingest &lt;path-or-git-url&gt; -o digest.txt</code>
          <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">CLI Ready</span>
        </div>
      </div>
    </div>
  );
};
export default GitIngestView;
