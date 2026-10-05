import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Upload } from 'lucide-react';
import { getNavPages, navGroups } from '../pages/registry';
import { useAppStore } from '../store';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activePage: string;
  onNavigate: (pageId: string) => void;
}

const presetRepos = [
  { key: 'petclinic', label: 'PetClinic', url: 'https://github.com/spring-projects/spring-petclinic' },
  { key: 'mybatis', label: 'MyBatis 3', url: 'https://github.com/mybatis/mybatis-3' },
  { key: 'dubbo', label: 'Dubbo', url: 'https://github.com/apache/dubbo' },
] as const;

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  activePage,
  onNavigate,
}) => {
  const {
    repoPath,
    setRepoPath,
    injectHallucination,
    setInjectHallucination,
    runAnalysis,
    uploadAndAnalyze,
    analysisError,
    isAnalyzing,
  } = useAppStore();

  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    repository: true,
    understand: true,
    explore: true,
    'ai-assistant': true,
    'code-review': true,
    config: true,
  });

  const pages = getNavPages();
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadAndAnalyze(e.target.files[0]);
      e.target.value = '';
    }
  };

  const toggleGroup = (groupId: string) => {
    setOpenGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  return (
    <aside
      className="flex flex-col h-screen border-r border-black dark:border-[#222328] bg-white dark:bg-[#0c0d10] text-[#0f172a] dark:text-[#f4f4f5] transition-all duration-140 shadow-[4px_0_0_0_#000000] dark:shadow-none"
      style={{
        width: isCollapsed ? '64px' : '260px',
        zIndex: 50,
      }}
      aria-label="Main navigation"
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-black dark:border-[#222328] bg-white dark:bg-[#0c0d10]">
        {!isCollapsed && (
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex items-center gap-1 flex-shrink-0">
              <span className="w-2.5 h-2.5 rounded-full bg-black dark:bg-zinc-100" />
              <span className="w-2.5 h-2.5 rounded-none bg-neutral-600 dark:bg-zinc-400" />
              <span
                className="w-2.5 h-2.5 bg-neutral-400 dark:bg-zinc-600"
                style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
              />
            </div>
            <div className="min-w-0">
              <h1 className="font-sans font-black text-xs text-black dark:text-white tracking-wider uppercase truncate">DEVLENSX</h1>
              <p className="text-[9px] font-sans font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 truncate">DEVELOPER OS</p>
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1 border border-black dark:border-[#2a2b32] bg-white dark:bg-[#141519] hover:bg-neutral-100 dark:hover:bg-[#1a1b22] text-black dark:text-zinc-200 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all"
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Target Repository Form */}
      {!isCollapsed && (
        <div className="p-3 border-b border-black dark:border-[#222328] bg-white dark:bg-[#0c0d10] space-y-3">
          <label className="font-sans font-bold text-[10px] uppercase tracking-wider text-neutral-700 dark:text-zinc-200 block mb-1">
            TARGET REPOSITORY
          </label>

          <div className="grid grid-cols-3 gap-1 mb-2">
            {presetRepos.map((repo) => (
              <button
                key={repo.key}
                onClick={() => { setRepoPath(repo.url); runAnalysis(repo.url); }}
                disabled={isAnalyzing}
                className={`text-[10px] font-sans font-bold uppercase px-1.5 py-1 border rounded-none transition-all truncate active:translate-x-[1px] active:translate-y-[1px] ${
                  repoPath.includes(repo.key)
                    ? 'sidebar-preset-active font-black shadow-[2px_2px_0px_0px_#000000] dark:shadow-none'
                    : 'border-black dark:border-zinc-700 bg-white dark:bg-[#141519] text-black dark:text-zinc-200 hover:bg-neutral-100 dark:hover:bg-[#1f2028]'
                }`}
                title={repo.url}
              >
                {repo.label}
              </button>
            ))}
          </div>

          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 font-mono text-xs text-black dark:text-zinc-300 font-bold">&gt;</span>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="repo path or URL"
              className="w-full pl-6 pr-2 py-1.5 text-xs font-mono border border-black dark:border-zinc-600 bg-white dark:bg-[#141519] text-black dark:text-zinc-100 focus:outline-none focus:border-black dark:focus:border-zinc-300 shadow-[2px_2px_0px_0px_#000000] dark:shadow-none placeholder-neutral-400 dark:placeholder-zinc-500"
              disabled={isAnalyzing}
            />
          </div>

          <div>
            <label className="font-sans font-bold text-[10px] uppercase tracking-wider text-neutral-700 dark:text-zinc-200 block mb-1">
              OR ARCHIVE
            </label>
            <label
              className="w-full flex items-center justify-center gap-2 p-2 text-xs font-sans font-bold uppercase border border-dashed border-black dark:border-zinc-600 bg-white dark:bg-[#141519] hover:bg-neutral-50 dark:hover:bg-[#1a1b22] cursor-pointer text-black dark:text-zinc-200 transition-colors shadow-[2px_2px_0px_0px_#000000] dark:shadow-none"
            >
              <Upload className="w-3.5 h-3.5 text-black dark:text-zinc-200" />
              <span>Upload .zip</span>
              <input type="file" accept=".zip" onChange={handleFileChange} className="hidden" disabled={isAnalyzing} />
            </label>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="hallucinationToggle"
              checked={injectHallucination}
              onChange={(e) => setInjectHallucination(e.target.checked)}
              className="rounded-none border border-black dark:border-zinc-500 accent-black cursor-pointer w-3.5 h-3.5"
            />
            <label htmlFor="hallucinationToggle" className="text-[11px] font-sans font-medium text-neutral-700 dark:text-zinc-200 flex-1 cursor-pointer select-none">
              Inject Rejection Test
            </label>
          </div>

          {analysisError && (
            <p className="text-xs font-mono leading-relaxed text-black dark:text-zinc-100 bg-neutral-100 dark:bg-zinc-900 p-2 border border-black dark:border-zinc-700" role="alert">
              {analysisError}
            </p>
          )}

          <button
            onClick={() => runAnalysis(repoPath)}
            disabled={isAnalyzing || !repoPath.trim()}
            className="w-full py-2.5 text-xs font-sans font-black uppercase tracking-wider sidebar-btn-analyze border shadow-[3px_3px_0px_0px_#000000] dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3 h-3 border-2 border-white dark:border-black border-t-transparent rounded-full animate-spin" />
                <span>ANALYZING...</span>
              </span>
            ) : (
              'ANALYZE REPOSITORY'
            )}
          </button>
        </div>
      )}

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-2 bg-white dark:bg-[#0c0d10]" aria-label="Views">
        {navGroups.map(group => {
          const groupPages = pages.filter(p => p.group === group.id);
          if (!groupPages.length) return null;
          const isOpen = openGroups[group.id];

          return (
            <div key={group.id} className="space-y-1">
              <button
                onClick={() => toggleGroup(group.id)}
                className="w-full flex items-center justify-between px-2 py-1 text-[10px] font-sans font-bold uppercase tracking-wider text-neutral-600 dark:text-zinc-300 hover:text-black dark:hover:text-white"
                aria-expanded={isOpen}
              >
                <span>{group.label}</span>
                {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-neutral-600 dark:text-zinc-300" /> : <ChevronRight className="w-3.5 h-3.5 text-neutral-600 dark:text-zinc-300" />}
              </button>

              {isOpen && (
                <div className="space-y-0.5">
                  {groupPages.map(page => {
                    const Icon = page.icon;
                    const isActive = activePage === page.id;
                    return (
                      <button
                        key={page.id}
                        onClick={() => onNavigate(page.id)}
                        className={`w-full flex items-center px-2.5 py-1.5 text-xs font-sans font-semibold uppercase tracking-wider rounded-none transition-all ${
                          isActive
                            ? 'sidebar-nav-item-active font-bold shadow-[2px_2px_0px_0px_#000000] dark:shadow-none'
                            : 'text-neutral-700 dark:text-zinc-200 hover:bg-neutral-100 dark:hover:bg-[#18191f] hover:text-black dark:hover:text-white border border-transparent'
                        }`}
                        aria-current={isActive ? 'page' : undefined}
                        title={isCollapsed ? `${page.label} — ${page.description}` : page.description}
                      >
                        {!isCollapsed && (
                          <>
                            <Icon className={`w-3.5 h-3.5 mr-2 flex-shrink-0 ${isActive ? 'sidebar-nav-icon' : 'text-neutral-600 dark:text-zinc-300'}`} />
                            <span className={`truncate ${isActive ? 'sidebar-nav-label' : ''}`}>{page.label}</span>
                            {page.badge && (
                              <span
                                className={`ml-auto text-[9px] font-mono font-bold px-1.5 py-0.5 border rounded-sm ${
                                  isActive
                                    ? 'border-white dark:border-cyan-500/40 bg-neutral-800 dark:bg-cyan-500/20 text-white dark:text-cyan-300'
                                    : 'border-black dark:border-zinc-700/80 bg-neutral-100 dark:bg-[#151722] text-black dark:text-zinc-300'
                                }`}
                              >
                                {page.badge}
                              </span>
                            )}
                          </>
                        )}
                        {isCollapsed && (
                          <span className="mx-auto" style={{ width: '24px' }}>
                            <Icon className={`w-4 h-4 mx-auto ${isActive ? 'sidebar-nav-icon' : 'text-neutral-500 dark:text-zinc-400'}`} />
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Status Footer */}
      <div className="p-3 border-t border-black dark:border-[#222328] bg-white dark:bg-[#0c0d10] flex items-center justify-between font-sans">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)] animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-black dark:text-emerald-400">SYS://ONLINE</span>
          </div>
        )}
        <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-neutral-500 dark:text-cyan-400/80">
          DEVLENSX OS
        </div>
      </div>
    </aside>
  );
};