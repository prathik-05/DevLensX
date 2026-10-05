import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store';
import {
  ingestRepoApi,
  getDigestDownloadUrl,
  analyzeFromIngestApi,
  type IngestResult,
  type IngestFileItem,
} from '../apiClient';
import {
  FolderTree,
  FileCode,
  Cpu,
  HardDrive,
  Copy,
  Check,
  Download,
  Play,
  Filter,
  RefreshCw,
  Sliders,
  ChevronRight,
  ChevronDown,
  CheckSquare,
  Square,
  AlertCircle,
  FileText,
  Sparkles,
} from 'lucide-react';
import { GlassPanel } from './GlassPanel';

interface TreeNode {
  name: string;
  fullPath: string;
  isDir: boolean;
  children: Record<string, TreeNode>;
  fileItem?: IngestFileItem;
}

export const IngestView: React.FC = () => {
  const navigate = useNavigate();
  const { repoPath, setRepoPath, setAnalysisData } = useAppStore();

  const [url, setUrl] = useState(repoPath || 'https://github.com/fastapi/fastapi');
  const [branch, setBranch] = useState('');
  const [includePatterns, setIncludePatterns] = useState('');
  const [excludePatterns, setExcludePatterns] = useState('');
  const [maxFileSizeKb, setMaxFileSizeKb] = useState(1024); // 1 MB default
  const [token, setToken] = useState('');

  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IngestResult | null>(null);

  // Set of excluded file paths unchecked by user
  const [deselectedPaths, setDeselectedPaths] = useState<Set<string>>(new Set());
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'digest' | 'tree' | 'files'>('digest');

  const handleIngest = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await ingestRepoApi(
        {
          url: url.trim(),
          branch: branch.trim() || undefined,
          include_patterns: includePatterns.trim() || undefined,
          exclude_patterns: excludePatterns.trim() || undefined,
          max_file_size: maxFileSizeKb * 1024,
          token: token.trim() || undefined,
        },
        true // full contents for tree inspection & live recompute
      );
      setResult(data);
      setDeselectedPaths(new Set());
      // Expand top-level dirs
      const initialExpanded = new Set<string>();
      data.files.forEach(f => {
        const parts = f.path.split('/');
        if (parts.length > 1) {
          initialExpanded.add(parts[0]);
        }
      });
      setExpandedDirs(initialExpanded);
    } catch (err: any) {
      setError(err?.message || 'Failed to ingest repository');
    } finally {
      setLoading(false);
    }
  };

  // Recomputed active files
  const activeFiles = useMemo(() => {
    if (!result) return [];
    return result.files.filter(f => !deselectedPaths.has(f.path));
  }, [result, deselectedPaths]);

  // Live statistics
  const activeTotalBytes = useMemo(() => {
    return activeFiles.reduce((acc, f) => acc + f.size, 0);
  }, [activeFiles]);

  const activeEstimatedTokens = useMemo(() => {
    return activeFiles.reduce((acc, f) => acc + f.tokens, 0);
  }, [activeFiles]);

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Live computed digest string
  const computedDigest = useMemo(() => {
    if (!result) return '';
    const chunks = [
      'Directory structure:',
      result.tree,
      '',
    ];
    activeFiles.forEach(f => {
      chunks.push('================================================');
      chunks.push(`FILE: ${f.path}`);
      chunks.push('================================================');
      chunks.push(f.content || '');
      chunks.push('');
    });
    return chunks.join('\n');
  }, [result, activeFiles]);

  // Preview cropped content (300k chars crop limit)
  const { previewText, isCropped } = useMemo(() => {
    const limit = 300000;
    if (computedDigest.length > limit) {
      return {
        previewText: `(Files content cropped to 300k characters, download full ingest to see more)\n\n${computedDigest.slice(0, limit)}`,
        isCropped: true,
      };
    }
    return {
      previewText: computedDigest,
      isCropped: false,
    };
  }, [computedDigest]);

  // Build tree hierarchy
  const fileTree = useMemo(() => {
    if (!result) return null;
    const root: TreeNode = {
      name: result.summary.repo_name,
      fullPath: '',
      isDir: true,
      children: {},
    };

    result.files.forEach(file => {
      const parts = file.path.split('/');
      let current = root;
      let currPath = '';

      parts.forEach((part, index) => {
        currPath = currPath ? `${currPath}/${part}` : part;
        const isLast = index === parts.length - 1;

        if (isLast) {
          current.children[part] = {
            name: part,
            fullPath: currPath,
            isDir: false,
            children: {},
            fileItem: file,
          };
        } else {
          if (!current.children[part]) {
            current.children[part] = {
              name: part,
              fullPath: currPath,
              isDir: true,
              children: {},
            };
          }
          current = current.children[part];
        }
      });
    });

    return root;
  }, [result]);

  const toggleDirectory = (dirPath: string) => {
    setExpandedDirs(prev => {
      const next = new Set(prev);
      if (next.has(dirPath)) next.delete(dirPath);
      else next.add(dirPath);
      return next;
    });
  };

  const toggleFile = (filePath: string) => {
    setDeselectedPaths(prev => {
      const next = new Set(prev);
      if (next.has(filePath)) next.delete(filePath);
      else next.add(filePath);
      return next;
    });
  };

  const selectAll = () => {
    setDeselectedPaths(new Set());
  };

  const deselectAll = () => {
    if (!result) return;
    setDeselectedPaths(new Set(result.files.map(f => f.path)));
  };

  const handleCopy = () => {
    if (!computedDigest) return;
    navigator.clipboard.writeText(computedDigest);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result) return;
    // If all files included, use backend download endpoint; otherwise download active selection
    if (deselectedPaths.size === 0) {
      window.open(getDigestDownloadUrl(result.id), '_blank');
    } else {
      const blob = new Blob([computedDigest], { type: 'text/plain;charset=utf-8' });
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = dlUrl;
      a.download = `${result.summary.repo_name}-digest.txt`;
      a.click();
      URL.revokeObjectURL(dlUrl);
    }
  };

  const handleAnalyzeFromIngest = async () => {
    if (!result) return;
    setAnalyzing(true);
    setError(null);
    try {
      const res = await analyzeFromIngestApi(result.id, url);
      if (res.repo_path) {
        setRepoPath(res.repo_path);
      }
      if (res.analysis) {
        setAnalysisData(res.analysis);
      }
      navigate('/overview');
    } catch (err: any) {
      setError(err?.message || 'Failed to analyze repository from ingest');
    } finally {
      setAnalyzing(false);
    }
  };

  // Render tree node component
  const renderTreeNode = (node: TreeNode, depth: number = 0) => {
    if (node.isDir) {
      const isExpanded = expandedDirs.has(node.fullPath);
      const childKeys = Object.keys(node.children).sort((a, b) => {
        const aIsDir = node.children[a].isDir;
        const bIsDir = node.children[b].isDir;
        if (aIsDir && !bIsDir) return -1;
        if (!aIsDir && bIsDir) return 1;
        return a.localeCompare(b);
      });

      return (
        <div key={node.fullPath || 'root'} className="text-xs font-mono">
          {node.fullPath && (
            <div
              onClick={() => toggleDirectory(node.fullPath)}
              className="flex items-center gap-1.5 py-1 px-2 rounded hover:bg-zinc-800/60 cursor-pointer select-none text-slate-300"
              style={{ paddingLeft: `${Math.max(8, depth * 16)}px` }}
            >
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              )}
              <FolderTree className="w-3.5 h-3.5 text-amber-400/80 shrink-0" />
              <span className="font-semibold text-slate-200">{node.name}</span>
            </div>
          )}
          {(!node.fullPath || isExpanded) && (
            <div>{childKeys.map(k => renderTreeNode(node.children[k], depth + 1))}</div>
          )}
        </div>
      );
    }

    const isSelected = !deselectedPaths.has(node.fullPath);
    return (
      <div
        key={node.fullPath}
        className={`flex items-center justify-between py-1 px-2 rounded hover:bg-zinc-800/40 select-none text-xs font-mono transition-colors ${
          isSelected ? 'text-slate-200' : 'text-slate-500 line-through'
        }`}
        style={{ paddingLeft: `${depth * 16}px` }}
      >
        <div
          onClick={() => toggleFile(node.fullPath)}
          className="flex items-center gap-2 cursor-pointer flex-1 min-w-0"
        >
          {isSelected ? (
            <CheckSquare className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          ) : (
            <Square className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
          )}
          <FileCode className="w-3.5 h-3.5 text-cyan-400/70 shrink-0" />
          <span className="truncate">{node.name}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500 shrink-0">
          <span>{node.fileItem?.language}</span>
          <span>{formatSize(node.fileItem?.size || 0)}</span>
          <span className="text-amber-500/80">{node.fileItem?.tokens} tok</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Banner & Header */}
      <GlassPanel className="p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-zinc-800/80 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
                <Sparkles className="w-6 h-6" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-slate-100 tracking-tight">Repo Ingest</h1>
                  <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    GitIngest Engine
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Converts GitHub repositories and local directories into LLM-optimized prompt digests with interactive filtering.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setUrl('https://github.com/fastapi/fastapi')}
              className="px-2.5 py-1 text-xs font-mono rounded-lg bg-zinc-900 border border-zinc-700/80 text-slate-300 hover:text-white hover:border-indigo-500 transition-colors"
            >
              fastapi
            </button>
            <button
              onClick={() => setUrl('d:/projects/DevLensX')}
              className="px-2.5 py-1 text-xs font-mono rounded-lg bg-zinc-900 border border-zinc-700/80 text-slate-300 hover:text-white hover:border-indigo-500 transition-colors"
            >
              DevLensX (local)
            </button>
            <button
              onClick={() => setUrl('https://github.com/pallets/flask')}
              className="px-2.5 py-1 text-xs font-mono rounded-lg bg-zinc-900 border border-zinc-700/80 text-slate-300 hover:text-white hover:border-indigo-500 transition-colors"
            >
              flask
            </button>
          </div>
        </div>

        {/* Primary Inputs */}
        <div className="space-y-3 pt-2">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 font-mono text-xs">
                SOURCE
              </div>
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo or local directory path..."
                className="w-full pl-20 pr-4 py-2.5 bg-black/60 border border-zinc-700 rounded-xl text-slate-100 text-xs font-mono focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="w-full sm:w-36">
              <input
                type="text"
                value={branch}
                onChange={e => setBranch(e.target.value)}
                placeholder="Branch / tag"
                className="w-full px-3 py-2.5 bg-black/60 border border-zinc-700 rounded-xl text-slate-100 text-xs font-mono focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowFilters(s => !s)}
                className={`px-3 py-2.5 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  showFilters
                    ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300'
                    : 'bg-zinc-900 border-zinc-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Filters</span>
              </button>

              <button
                onClick={handleIngest}
                disabled={loading || !url.trim()}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-all shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>{loading ? 'Ingesting...' : 'Ingest Repo'}</span>
              </button>
            </div>
          </div>

          {/* Advanced Filter Drawer */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-xl bg-black/40 border border-zinc-800 text-xs">
              <div>
                <label className="text-slate-400 font-mono block mb-1">Include Patterns (glob):</label>
                <input
                  type="text"
                  value={includePatterns}
                  onChange={e => setIncludePatterns(e.target.value)}
                  placeholder="e.g. src/*, *.py, *.ts"
                  className="w-full px-3 py-1.5 bg-zinc-900/90 border border-zinc-700/80 rounded-lg text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="text-slate-400 font-mono block mb-1">Exclude Patterns (glob):</label>
                <input
                  type="text"
                  value={excludePatterns}
                  onChange={e => setExcludePatterns(e.target.value)}
                  placeholder="e.g. tests/*, docs/*"
                  className="w-full px-3 py-1.5 bg-zinc-900/90 border border-zinc-700/80 rounded-lg text-slate-200 font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-slate-400 font-mono flex items-center gap-1">
                    <Sliders className="w-3 h-3 text-indigo-400" />
                    <span>Max File Size:</span>
                  </label>
                  <span className="font-mono text-indigo-400">{maxFileSizeKb} KB</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="5120"
                  step="50"
                  value={maxFileSizeKb}
                  onChange={e => setMaxFileSizeKb(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div className="md:col-span-3 pt-1 border-t border-zinc-800/80">
                <label className="text-slate-400 font-mono block mb-1">GitHub Access Token (Optional, for private repos or higher rate limits):</label>
                <input
                  type="password"
                  value={token}
                  onChange={e => setToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxx (never logged or shared)"
                  className="w-full px-3 py-1.5 bg-zinc-900/90 border border-zinc-700/80 rounded-lg text-slate-200 font-mono"
                />
              </div>
            </div>
          )}
        </div>
      </GlassPanel>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && !error && (
        <GlassPanel className="p-12 text-center rounded-2xl border border-zinc-800 space-y-3">
          <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 w-fit mx-auto border border-indigo-500/20">
            <FolderTree className="w-8 h-8" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">No Repository Ingested Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Provide a GitHub URL or local path above to generate a structured, prompt-ready codebase digest with directory tree, live token counts, and 1-click DevLensX analysis.
          </p>
        </GlassPanel>
      )}

      {/* Results Workspace */}
      {result && (
        <div className="space-y-6">
          {/* Summary Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                <span>Active Files</span>
              </div>
              <div className="text-2xl font-bold text-slate-100 font-mono">
                {activeFiles.length}
                <span className="text-xs text-slate-500 ml-1.5 font-normal">/ {result.summary.file_count}</span>
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
                <span>Digest Size</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {formatSize(activeTotalBytes)}
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-amber-400" />
                <span>Estimated Tokens</span>
              </div>
              <div className="text-2xl font-bold text-amber-400 font-mono">
                {activeEstimatedTokens >= 1000
                  ? `${(activeEstimatedTokens / 1000).toFixed(1)}k`
                  : activeEstimatedTokens}
              </div>
            </GlassPanel>

            <GlassPanel className="p-4 rounded-xl border border-zinc-800 bg-[#11131a]/80 space-y-1">
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <FolderTree className="w-3.5 h-3.5 text-purple-400" />
                <span>Repo & Branch</span>
              </div>
              <div className="text-sm font-bold text-purple-300 font-mono truncate">
                {result.summary.repo_name}
              </div>
              <div className="text-[10px] text-slate-500 font-mono truncate">
                {result.summary.branch} @ {result.summary.commit_sha.slice(0, 8)}
              </div>
            </GlassPanel>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('digest')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'digest'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white bg-zinc-800/60'
                }`}
              >
                Prompt Digest
              </button>
              <button
                onClick={() => setActiveTab('tree')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'tree'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white bg-zinc-800/60'
                }`}
              >
                Interactive Tree ({activeFiles.length})
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied Prompt!' : 'Copy Digest'}</span>
              </button>

              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-slate-200 text-xs font-semibold border border-zinc-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download .txt</span>
              </button>

              <button
                onClick={handleAnalyzeFromIngest}
                disabled={analyzing}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50"
              >
                <Play className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                <span>{analyzing ? 'Analyzing...' : 'Analyze with DevLensX'}</span>
              </button>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Interactive File Tree with checkboxes */}
            <div className="lg:col-span-4 rounded-2xl border border-zinc-800 bg-[#0d0f14] overflow-hidden flex flex-col h-[650px]">
              <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-zinc-800 bg-zinc-950/70 text-xs font-mono text-slate-300">
                <span className="font-semibold">File Selection</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={selectAll}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                  >
                    Select All
                  </button>
                  <span className="text-zinc-600">|</span>
                  <button
                    onClick={deselectAll}
                    className="text-[10px] text-slate-500 hover:text-slate-400 underline cursor-pointer"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <div className="p-3 overflow-y-auto flex-1 space-y-1">
                {fileTree && renderTreeNode(fileTree)}
              </div>
            </div>

            {/* Right Column: Digest Preview / ASCII Tree */}
            <div className="lg:col-span-8 rounded-2xl border border-zinc-800 bg-[#0d0f14] overflow-hidden flex flex-col h-[650px]">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-950/70 text-xs font-mono text-slate-400">
                <span>
                  {activeTab === 'digest'
                    ? 'Prompt Digest (Single LLM-friendly context)'
                    : 'ASCII Directory Tree'}
                </span>
                <div className="flex items-center gap-3">
                  {isCropped && activeTab === 'digest' && (
                    <span className="text-amber-400 text-[11px] font-sans font-medium">
                      Preview cropped to 300k chars
                    </span>
                  )}
                  <span>{activeFiles.length} files selected</span>
                </div>
              </div>

              <div className="p-4 overflow-auto flex-1 bg-black/40">
                {activeTab === 'digest' ? (
                  <pre className="text-xs font-mono text-slate-300 leading-relaxed whitespace-pre select-all">
                    {previewText}
                  </pre>
                ) : (
                  <pre className="text-xs font-mono text-emerald-400/90 leading-relaxed whitespace-pre select-all">
                    {result.tree}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IngestView;
