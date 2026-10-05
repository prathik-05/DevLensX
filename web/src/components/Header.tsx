import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, PanelLeft, PanelRight, Layers, FolderGit2, GitBranch } from 'lucide-react';
import { getCommandActions, searchPages } from '../pages/registry';
import { useAppStore } from '../store';
import { useWorkspaceContext } from '../workspaceContext';
import { ThemeToggle } from './ThemeToggle';

interface HeaderProps {
  activePage: string;
  onNavigate: (pageId: string) => void;
  onToggleSidebar: () => void;
  sidebarCollapsed: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activePage,
  onNavigate,
  onToggleSidebar,
  sidebarCollapsed,
}) => {
  const navigate = useNavigate();
  const { repoPath } = useAppStore();
  const runAnalysis = useAppStore(s => s.runAnalysis);
  const theme = useAppStore(s => s.theme);
  const analysisId = useAppStore(s => s.analysisId);

  const {
    workspace_name,
    repository_id,
    analysis_run_id,
    commit_hash,
    repositories,
    switchRepository,
  } = useWorkspaceContext();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdQuery, setCmdQuery] = useState('');
  const [cmdSelected, setCmdSelected] = useState(0);
  const cmdInputRef = useRef<HTMLInputElement>(null);
  const cmdResultsRef = useRef<HTMLDivElement>(null);

  const actions = getCommandActions();
  const filteredActions = cmdQuery
    ? actions.filter(a =>
        a.label.toLowerCase().includes(cmdQuery.toLowerCase()) ||
        a.description.toLowerCase().includes(cmdQuery.toLowerCase()) ||
        a.keywords.some(k => k.toLowerCase().includes(cmdQuery.toLowerCase()))
      )
    : actions;

  const pages = searchPages(cmdQuery);
  const pageActions = pages.map(p => ({
    id: `nav:${p.id}`,
    label: p.label,
    description: p.description,
    icon: p.icon,
    action: 'navigate' as const,
    payload: p.path,
    keywords: ['go to', 'open', 'navigate', ...p.keywords],
  }));

  const customActions = filteredActions.filter(a => a.action === 'custom');
  const seenPageIds = new Set(pageActions.map(a => a.id));
  const allResults = [...pageActions, ...customActions.filter(a => !seenPageIds.has(a.id))];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(true);
        setCmdQuery('');
        setCmdSelected(0);
      }
      if (e.key === 'Escape' && cmdOpen) {
        setCmdOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [cmdOpen]);

  useEffect(() => {
    if (cmdOpen) {
      setTimeout(() => cmdInputRef.current?.focus(), 0);
    }
  }, [cmdOpen]);

  const handleActionSelect = (action: typeof allResults[0]) => {
    if (action.action === 'navigate') {
      const pageId = action.payload.replace('/', '');
      onNavigate(pageId);
    } else {
      handleCustomAction(action.payload);
    }
    setCmdOpen(false);
    setCmdQuery('');
  };

  const downloadText = (filename: string, text: string, mime = 'text/markdown') => {
    const blob = new Blob([text], { type: `${mime};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleCustomAction = (payload: any) => {
    switch (payload.type) {
      case 'analyze':
        runAnalysis(repoPath);
        onNavigate('overview');
        break;
      case 'switch-repo':
        navigate('/');
        break;
      case 'export-wiki': {
        const runId = useAppStore.getState().analysisId;
        if (!runId) break;
        (async () => {
          try {
            const { fetchWiki } = await import('../apiClient');
            const tree = await fetchWiki(runId);
            const pages = tree?.page_tree || [];
            const { fetchWikiPage } = await import('../apiClient');
            let md = `# Wiki Export — ${runId}\n\n`;
            for (const p of pages) {
              const content = await fetchWikiPage(runId, p.id).catch(() => null);
              md += `\n\n## ${p.title}\n\n`;
              for (const s of content?.sections || []) {
                md += `### ${s.heading}\n\n${s.content || ''}\n\n`;
              }
            }
            downloadText(`wiki-${runId}.md`, md);
          } catch {
            /* offline or failed fetch: no silent partial file */
          }
        })();
        break;
      }
      case 'code-review':
        onNavigate('code-turtle');
        break; // Code Turtle — AI Review
      case 'clear-cache':
        // All analysis state is in-memory: a reload is a full, honest reset.
        window.location.reload();
        break;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCmdSelected(prev => Math.min(prev + 1, allResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCmdSelected(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (allResults[cmdSelected]) handleActionSelect(allResults[cmdSelected]);
    } else if (e.key === 'Escape') {
      setCmdOpen(false);
    }
  };

  return (
    <>
      <header className="border-b border-black dark:border-[#222328] px-4 py-2.5 dl-flex-between sticky top-0 z-40 bg-white dark:bg-[#0c0d10] shadow-[0_2px_0_0_#000000] dark:shadow-none">
        <div className="dl-flex-gap-3 items-center">
          <button
            onClick={onToggleSidebar}
            className="p-1.5 border border-black dark:border-[#2a2b32] bg-white dark:bg-[#141519] hover:bg-neutral-100 dark:hover:bg-[#1c1d24] text-black dark:text-zinc-200 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all"
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <PanelLeft className="w-4 h-4" />
          </button>

          <button
            onClick={() => onNavigate('overview')}
            className="flex items-center gap-2.5 px-2.5 py-1 border border-black dark:border-[#2a2b32] bg-white dark:bg-[#141519] shadow-[2px_2px_0px_0px_#000000] dark:shadow-none hover:bg-neutral-100 dark:hover:bg-[#1a1b22] active:translate-x-[1px] active:translate-y-[1px] transition-all"
            title="DevLensX Core"
          >
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-black dark:bg-zinc-100" title="Circle" />
              <span className="w-2.5 h-2.5 rounded-none bg-neutral-500 dark:bg-zinc-400" title="Square" />
              <span
                className="w-2.5 h-2.5 bg-neutral-400 dark:bg-zinc-600"
                style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
                title="Triangle"
              />
            </div>
            <span className="font-sans text-xs font-black tracking-wider text-black dark:text-white uppercase">
              DEVLENSX://CORE
            </span>
          </button>

          <div className="w-px h-5 bg-neutral-300 dark:bg-zinc-800 mx-1 hidden md:block" />

          {/* Clean Modern View Switcher Rail */}
          <nav className="hidden lg:flex items-center gap-1 text-[11px] font-mono font-medium" aria-label="Quick navigation">
            {[
              { id: 'overview', label: '01 OVERVIEW' },
              { id: 'wiki', label: '02 WIKI' },
              { id: 'code-turtle', label: '03 CODE TURTLE' },
              { id: 'changelog', label: '04 IMPACT' },
              { id: 'evaluation', label: '05 EVAL' }
            ].map(tab => {
              const isActive = activePage === tab.id || (tab.id === 'code-turtle' && activePage === 'code-rabbit');
              return (
                <button
                  key={tab.id}
                  onClick={() => onNavigate(tab.id)}
                  className={`px-2.5 py-1 text-xs transition-all border ${
                    isActive
                      ? 'border-black dark:border-cyan-500/50 bg-black text-white dark:bg-cyan-500/15 dark:text-cyan-300 shadow-[2px_2px_0px_0px_#000000] dark:shadow-[0_0_12px_rgba(6,182,212,0.15)] font-bold'
                      : 'border-transparent text-neutral-600 dark:text-zinc-400 hover:text-black dark:hover:text-zinc-200 hover:bg-neutral-100 dark:hover:bg-zinc-800/60'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Multi-Repo Federation Status & Selector */}
          <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 bg-white dark:bg-[#11131a] border border-black dark:border-zinc-800/80 text-xs font-mono shadow-[2px_2px_0px_0px_#000000] dark:shadow-none ml-2">
            <div className="flex items-center gap-1 text-neutral-500 dark:text-zinc-400">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              <span className="font-semibold text-black dark:text-zinc-200">
                Workspace: {workspace_name || 'My Workspace'}
              </span>
            </div>
            <span className="text-neutral-300 dark:text-zinc-700">|</span>
            <div className="flex items-center gap-1">
              <FolderGit2 className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-neutral-500 dark:text-zinc-400">Repo:</span>
              {repositories && repositories.length > 1 ? (
                <select
                  value={repository_id || (repositories[0]?.repository_id ?? '')}
                  onChange={(e) => switchRepository && switchRepository(e.target.value)}
                  className="bg-transparent border-none text-xs font-bold text-black dark:text-zinc-100 cursor-pointer focus:ring-0 p-0"
                  aria-label="Select Repository"
                >
                  {repositories.map((r: any) => (
                    <option key={r.repository_id} value={r.repository_id} className="dark:bg-[#1a1b22]">
                      {r.repo_name || r.repository_id}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="font-bold text-black dark:text-zinc-100 truncate max-w-[150px]" title={repository_id || repoPath || 'No repository'}>
                  {repository_id || (repoPath ? repoPath.split(/[\\/]/).pop() : 'No repository')}
                </span>
              )}
            </div>
            {(analysis_run_id || analysisId) && (
              <>
                <span className="text-neutral-300 dark:text-zinc-700">|</span>
                <span className="text-[10px] text-neutral-600 dark:text-zinc-400 flex items-center gap-1" title={`Run: ${analysis_run_id || analysisId}`}>
                  <span>Run:</span>
                  <span className="text-emerald-400 font-mono font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30">
                    {(analysis_run_id || analysisId || '').slice(0, 10)}
                  </span>
                </span>
              </>
            )}
            {commit_hash && (
              <>
                <span className="text-neutral-300 dark:text-zinc-700">|</span>
                <span className="text-[10px] text-neutral-500 dark:text-zinc-400" title={`Commit: ${commit_hash}`}>
                  <GitBranch className="inline w-3 h-3 text-purple-400 mr-0.5" />
                  {commit_hash.slice(0, 7)}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Command Search Bar */}
        <div className="relative flex-1 max-w-md mx-4">
          <button
            onClick={() => { setCmdOpen(true); setCmdQuery(''); setCmdSelected(0); }}
            className="w-full pl-9 pr-12 py-1.5 text-left flex items-center gap-2 bg-white dark:bg-[#141519] border border-black dark:border-[#2a2b32] shadow-[2px_2px_0px_0px_#000000] dark:shadow-none rounded-none active:translate-x-[1px] active:translate-y-[1px] transition-all"
            aria-label="Open command palette"
          >
            <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-xs text-black dark:text-zinc-400 font-bold">&gt;</span>
            <span className="text-xs font-sans text-neutral-500 dark:text-zinc-400">search system, actions, symbols…</span>
          </button>
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-bold font-mono bg-neutral-100 dark:bg-zinc-800 text-black dark:text-zinc-300 border border-black dark:border-zinc-700">⌘K</kbd>
        </div>

        {/* Right Status Indicator & Theme Toggle */}
        <div className="dl-flex-gap-3 items-center ml-auto">
          {/* Theme Toggle */}
          <ThemeToggle />

          <div className="flex items-center gap-2 text-[10px] font-sans font-bold uppercase px-2.5 py-1 bg-white dark:bg-[#141519] border border-black dark:border-[#2a2b32] text-black dark:text-zinc-300 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)] animate-pulse" />
            <span>SYSTEM ONLINE</span>
          </div>
          <button
            onClick={onToggleSidebar}
            className="p-1.5 border border-black dark:border-[#2a2b32] bg-white dark:bg-[#141519] text-black dark:text-zinc-200 sm:hidden"
            aria-label="Toggle sidebar"
          >
            <PanelRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Command Palette */}
      {cmdOpen && (
        <div className="dl-cmd-overlay" onClick={() => setCmdOpen(false)}>
          <div className="dl-cmd-window animate-in fade-in duration-100" onClick={e => e.stopPropagation()} ref={cmdResultsRef}>
            <div className="dl-cmd-input-wrapper relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--dl-text-muted)]" />
              <input
                ref={cmdInputRef}
                type="text"
                value={cmdQuery}
                onChange={e => { setCmdQuery(e.target.value); setCmdSelected(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Type to search..."
                className="dl-input dl-input-mono w-full pl-10 pr-8 bg-transparent border-none focus:ring-0 focus:shadow-none"
                style={{ fontSize: '14px' }}
                autoFocus
              />
            </div>

            <div className="dl-cmd-results">
              {allResults.length === 0 ? (
                <div className="p-4 text-center text-[var(--dl-text-dim)] text-sm">
                  No matches for &ldquo;{cmdQuery}&rdquo;
                </div>
              ) : (
                allResults.map((action, idx) => {
                  const Icon = action.icon;
                  const isSelected = idx === cmdSelected;
                  return (
                    <button
                      key={action.id}
                      onClick={() => handleActionSelect(action)}
                      onMouseEnter={() => setCmdSelected(idx)}
                      className={`dl-cmd-item ${isSelected ? 'selected' : ''}`}
                      style={{ background: isSelected ? 'var(--dl-surface-hover)' : 'transparent' }}
                    >
                      <span className={isSelected ? 'text-[var(--dl-accent)]' : 'text-[var(--dl-text-muted)]'}><Icon className="dl-cmd-item-icon w-4 h-4" /></span>
                      <div className="flex-1 min-w-0">
                        <div className="dl-cmd-item-title truncate" style={{ color: isSelected ? 'var(--dl-text-strong)' : 'var(--dl-text)' }}>
                          {action.label}
                        </div>
                        <div className="dl-cmd-item-desc truncate">{action.description}</div>
                      </div>
                      <kbd className="dl-cmd-item-shortcut dl-kbd">↵</kbd>
                    </button>
                  );
                })
              )}
            </div>

            <div className="px-3 py-2 border-t text-right" style={{ borderColor: 'var(--dl-panel-border)' }}>
              <kbd className="dl-kbd mr-2">Esc</kbd>
              <span className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>Close</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};