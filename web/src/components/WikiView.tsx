import React, { useEffect, useState, useRef } from 'react';
import {
  fetchWiki,
  fetchWikiPage,
  fetchWikiProviderStatus,
  askWikiCopilot,
  type WikiProviderStatus,
} from '../apiClient';
import {
  BookOpen, ChevronDown, ChevronRight, GitCommit, FileCode, ArrowRight,
  Layers, Zap, AlertTriangle, Compass, Sparkles, Send, Loader2, Key,
  ShieldCheck, HelpCircle, Rocket, Cpu, Database, Settings as SettingsIcon, Link as LinkIcon,
} from 'lucide-react';
import { useWikiContext, type WikiPageTreeItem } from '../wikiContext';
import { useWorkspaceContext } from '../workspaceContext';
import { EvidenceBadge } from './EvidenceBadge';
import type { Verdict } from '../evidence';
import mermaid from 'mermaid';
import { GlassPanel } from './GlassPanel';
import { Badge } from './Badge';
import { WikiSectionSkeleton } from './Skeleton';
import { GitIngestView } from './GitIngestView';

let _wikiMermaidTheme: 'dark' | 'default' | null = null;
function ensureWikiMermaidTheme() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const targetTheme = isLight ? 'default' : 'dark';
  if (_wikiMermaidTheme !== targetTheme) {
    mermaid.initialize({
      startOnLoad: false,
      theme: targetTheme,
      securityLevel: 'loose',
      fontFamily: 'ui-monospace, monospace',
    });
    _wikiMermaidTheme = targetTheme;
  }
}

type Category =
  | 'Overview'
  | 'Getting Started'
  | 'Architecture'
  | 'Components'
  | 'Modules'
  | 'API Reference'
  | 'Data Model'
  | 'Configuration'
  | 'References'
  | 'Change Impact';

const CATEGORY_ORDER: Category[] = [
  'Overview',
  'Getting Started',
  'Architecture',
  'Components',
  'Modules',
  'API Reference',
  'Data Model',
  'Configuration',
  'References',
  'Change Impact',
];

const CATEGORY_ICONS: Record<Category, React.ComponentType<{ className?: string }>> = {
  Overview: Compass,
  'Getting Started': Rocket,
  Architecture: Layers,
  Components: Cpu,
  Modules: BookOpen,
  'API Reference': Zap,
  'Data Model': Database,
  Configuration: SettingsIcon,
  References: LinkIcon,
  'Change Impact': AlertTriangle,
};

function categorize(item: WikiPageTreeItem): Category {
  const id = (item.id || '').toLowerCase();
  const t = (item.title || '').toLowerCase();
  const p = (item.parent || '').toLowerCase();
  const tp = (item.type || '').toLowerCase();
  if (id === 'overview' || t === 'overview') return 'Overview';
  if (id.includes('getting-started') || t.includes('getting started') || tp === 'guide') return 'Getting Started';
  if (id === 'architecture' || t.includes('architecture') || tp === 'architecture') return 'Architecture';
  if (id === 'components' || t.includes('component') || tp === 'components') return 'Components';
  if (p === 'modules' || tp === 'module' || id.startsWith('module') || t.includes('module')) return 'Modules';
  if (id.includes('api') || t.includes('api') || t.includes('endpoint') || t.includes('reference') || tp === 'api') return 'API Reference';
  if (id.includes('data-model') || t.includes('data model') || t.includes('database') || tp === 'database') return 'Data Model';
  if (id.includes('configuration') || t.includes('configuration') || tp === 'config') return 'Configuration';
  if (id.includes('references') || t.includes('references') || tp === 'references') return 'References';
  if (id.includes('change') || id.includes('impact') || t.includes('change') || t.includes('impact') || tp === 'impact') return 'Change Impact';
  return 'Overview';
}

function cleanHeading(heading: string): string {
  if (!heading) return '';
  const h = heading.trim();
  if (h.includes('Overview & Architecture Role')) return 'What This Repository Does';
  if (h.includes('Component Structure & Responsibilities')) return 'Core Components & Responsibilities';
  if (h.includes('Interactions & Dependencies')) return 'System Interactions & Dependencies';
  if (h.includes('Source Evidence Provenance')) return 'Source Code Provenance';
  return h.replace(/^\d+\.\s*/, '');
}

function groupByCategory(tree: WikiPageTreeItem[]): Record<Category, WikiPageTreeItem[]> {
  const grouped: Record<Category, WikiPageTreeItem[]> = {
    'Overview': [],
    'Getting Started': [],
    'Architecture': [],
    'Components': [],
    'Modules': [],
    'API Reference': [],
    'Data Model': [],
    'Configuration': [],
    'References': [],
    'Change Impact': [],
  };
  tree.forEach(item => { grouped[categorize(item)].push(item); });
  return grouped;
}

function verdictToBadge(verdict?: string | null): Verdict {
  if (!verdict) return 'NOT_VERIFIED';
  const v = verdict.toUpperCase();
  if (v === 'VERIFIED' || v.includes('VERIFIED')) return 'VERIFIED';
  if (v.includes('SUGGESTION') || v.includes('AI_SUGGESTION')) return 'AI_SUGGESTION';
  if (v.includes('INSUFFICIENT')) return 'INSUFFICIENT_EVIDENCE';
  return 'NOT_VERIFIED';
}

const MermaidBlock: React.FC<{ code: string }> = ({ code }) => {
  const [svg, setSvg] = useState<string | null>(null);
  const [renderErr, setRenderErr] = useState(false);
  const idRef = useRef(`wiki-mermaid-${Math.random().toString(36).slice(2, 9)}`);
  const [themeTick, setThemeTick] = useState(0);

  useEffect(() => {
    const obs = new MutationObserver(() => {
      _wikiMermaidTheme = null;
      setThemeTick(t => t + 1);
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!code?.trim()) return;
    ensureWikiMermaidTheme();
    mermaid.render(idRef.current + '-' + Date.now(), code)
      .then(({ svg }: { svg: string }) => {
        if (!cancelled) {
          setSvg(svg);
          setRenderErr(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSvg(null);
          setRenderErr(true);
        }
      });
    return () => { cancelled = true; };
  }, [code, themeTick]);

  if (renderErr) {
    return (
      <div className="rounded-sm p-3 border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#12131a] text-xs font-mono text-slate-600 dark:text-slate-400">
        <div className="dl-panel-label text-xs mb-1">ARCHITECTURE DIAGRAM (SOURCE)</div>
        <pre className="whitespace-pre overflow-x-auto text-[11px]">{code}</pre>
      </div>
    );
  }

  if (svg) {
    return (
      <div
        className="overflow-x-auto p-3 rounded-sm border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#12131a]"
        role="figure"
        aria-label="Repository Architecture Diagram"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    );
  }

  return (
    <div className="rounded-sm p-3 border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#12131a] animate-pulse">
      <div className="h-24 flex items-center justify-center text-xs font-mono text-slate-400">
        Rendering diagram…
      </div>
    </div>
  );
};

const CrossLinkedText: React.FC<{
  text: string;
  pagesSummary: Record<string, string>;
  pageTree: WikiPageTreeItem[];
  onNavigate: (pageId: string) => void;
}> = ({ text, pagesSummary, pageTree, onNavigate }) => {
  const [hover, setHover] = useState<{ label: string; target: string; blurb: string; x: number; y: number } | null>(null);
  const parts: React.ReactNode[] = [];
  const re = /\[([^\]]+)\]\(#([^)]+)\)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  const titleOf = (id: string) => pageTree.find(p => p.id === id)?.title || id;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(<span key={key++}>{text.slice(last, m.index)}</span>);
    const label = m[1];
    const target = m[2];
    const blurb = pagesSummary[target] || titleOf(target);
    const showPreview = (e: React.SyntheticEvent) => {
      const r = (e.currentTarget as HTMLButtonElement).getBoundingClientRect();
      setHover({ label, target, blurb: blurb.slice(0, 220), x: r.left, y: r.bottom + 6 });
    };
    parts.push(
      <button
        key={key++}
        onClick={() => onNavigate(target)}
        onMouseEnter={showPreview}
        onMouseLeave={() => setHover(null)}
        onFocus={showPreview}
        onBlur={() => setHover(null)}
        className="underline underline-offset-2"
        style={{ color: 'var(--dl-accent)' }}
        title={titleOf(target)}
      >
        {label}
      </button>
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(<span key={key++}>{text.slice(last)}</span>);
  return (
    <span className="relative">
      {parts}
      {hover && (
        <span
          className="fixed z-50 w-64 p-3 rounded-sm text-left"
          style={{ left: Math.min(hover.x, window.innerWidth - 280), top: hover.y, background: 'var(--dl-panel)', border: '1px solid var(--dl-panel-border)', boxShadow: '0 16px 48px -16px rgba(0,0,0,0.8)' }}
        >
          <span className="block text-xs font-bold font-mono text-black dark:text-white">{hover.label}</span>
          <span className="block text-[11px] mt-1 leading-relaxed" style={{ color: 'var(--dl-text-dim)' }}>{hover.blurb}</span>
          <span className="block text-[10px] font-mono mt-1.5" style={{ color: 'var(--dl-accent)' }}>→ {titleOf(hover.target)} (click to open)</span>
        </span>
      )}
    </span>
  );
};

interface SectionViewProps {
  section: any;
  idx: number;
  pagesSummary: Record<string, string>;
  pageTree: WikiPageTreeItem[];
  onNavigate: (pageId: string) => void;
  onExpandDiagram: (code: string) => void;
}

const SectionView: React.FC<SectionViewProps> = ({ section, idx, pagesSummary, pageTree, onNavigate, onExpandDiagram }) => {
  const verdict: Verdict = verdictToBadge(section.verdict);
  const headingText = cleanHeading(section.heading);
  const anchor = `sec-${idx}-${String(headingText || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)}`;
  const hasMermaid = !!section.mermaid;

  return (
    <section data-section={headingText} id={anchor} className="dl-prose space-y-4 scroll-mt-4">
      <div className="flex items-start justify-between gap-4 pb-3 border-b" style={{ borderColor: 'var(--dl-panel-border)' }}>
        <div className="flex-1">
          <h3 className="text-[15px] font-semibold text-slate-900 dark:text-white mb-1.5">{headingText}</h3>
          <EvidenceBadge verdict={verdict} />
        </div>
      </div>

      <div className="space-y-4">
        <CrossLinkedText text={String(section.content || '')} pagesSummary={pagesSummary} pageTree={pageTree} onNavigate={onNavigate} />

        {hasMermaid && (
          <div className="space-y-2">
            <MermaidBlock code={section.mermaid} />
            <button onClick={() => onExpandDiagram(section.mermaid)} className="text-[11px] font-mono underline underline-offset-2 flex items-center gap-1.5" style={{ color: 'var(--dl-accent)' }}>
              <FileCode className="w-3.5 h-3.5" />
              Expand diagram
            </button>
          </div>
        )}

        {section.claims && section.claims.length > 0 && (
          <div className="space-y-1.5 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/60">
            <div className="text-[11px] font-mono font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mb-1.5">
              <span>VERIFIED FACTUAL CLAIMS:</span>
              <Badge variant="finding-perf" size="sm">{section.claims.length}</Badge>
            </div>
            <div className="space-y-1">
              {section.claims.map((cl: any, ci: number) => {
                const isVerified = String(cl.verdict || '').includes('VERIFIED');
                const isInsufficient = String(cl.verdict || '').includes('INSUFFICIENT');
                return (
                  <div
                    key={ci}
                    className="p-2 rounded-sm border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-[#12131a] flex items-center gap-2 flex-wrap text-[11px] font-mono"
                  >
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                      style={{
                        background: isVerified
                          ? 'var(--semantic-verified-bg)'
                          : isInsufficient
                          ? 'var(--semantic-insufficient-bg)'
                          : 'var(--semantic-ai-suggestion-bg)',
                        color: isVerified
                          ? 'var(--semantic-verified)'
                          : isInsufficient
                          ? 'var(--semantic-insufficient)'
                          : 'var(--semantic-ai-suggestion)',
                      }}
                    >
                      {cl.verdict || 'CLAIM'}
                    </span>
                    <span className="font-bold text-slate-900 dark:text-white">{cl.subject}</span>
                    <ArrowRight className="w-3 h-3 text-slate-400" />
                    <span className="text-sky-600 dark:text-sky-400 font-semibold">{cl.predicate}</span>
                    <ArrowRight className="w-3 h-3 text-slate-400" />
                    <span className="font-bold text-slate-900 dark:text-white">{cl.object}</span>
                    {cl.evidence_source && (
                      <span className="ml-auto text-[10px] text-slate-500 truncate max-w-xs" title={cl.evidence_source}>
                        📍 {cl.evidence_source}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {section.collapsible && (
        <details className="dl-details mt-4">
          <summary>Details — deep-dive facts (click to expand)</summary>
          <div className="dl-details-body space-y-3 text-[12px] leading-relaxed">
            {String(section.content || '')}
          </div>
        </details>
      )}
    </section>
  );
};

export const WikiView: React.FC = () => {
  const { analysisId, pageTree, pagesSummary, activePageId, activePageContent, loading, setAnalysisId, setWikiData, setActivePage, setActivePageContent } = useWikiContext();
  const { analysis_run_id } = useWorkspaceContext();
  const effectiveId = analysisId || analysis_run_id;
  const [search, setSearch] = useState('');
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [expandedDiagram, setExpandedDiagram] = useState<string | null>(null);
  const [openSections, setOpenSections] = useState<Record<Category, boolean>>({
    'Overview': true,
    'Getting Started': true,
    'Architecture': true,
    'Components': true,
    'Modules': true,
    'API Reference': true,
    'Data Model': true,
    'Configuration': true,
    'References': true,
    'Change Impact': true,
  });

  // Copilot Q&A state
  const [rightTab, setRightTab] = useState<'toc' | 'qa'>('toc');
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState<Array<{ question: string; answer: string; citations: string[]; verdict: string }>>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<WikiProviderStatus | null>(null);
  const [showKeyHint, setShowKeyHint] = useState(false);

  const [wikiMode, setWikiMode] = useState<'digest' | 'docs'>('digest');

  const contentRef = useRef<HTMLDivElement>(null);
  const qaScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchWikiProviderStatus().then(status => {
      if (status) setProviderStatus(status);
    });
  }, []);

  useEffect(() => {
    if (analysis_run_id && analysis_run_id !== analysisId) {
      setAnalysisId(analysis_run_id);
    } else if (!effectiveId) {
      fetch('/api/wiki')
        .then(r => (r.ok ? r.json() : null))
        .then(d => {
          if (d?.analysis_run_id) setAnalysisId(d.analysis_run_id);
        })
        .catch(() => {});
    }
  }, [analysis_run_id, analysisId, effectiveId, setAnalysisId]);

  useEffect(() => {
    if (!effectiveId) return;
    let cancelled = false;
    const controller = new AbortController();
    fetchWiki(effectiveId, controller.signal).then(data => {
      if (cancelled || controller.signal.aborted) return;
      const tree: WikiPageTreeItem[] = (data?.page_tree || data?.pages || []) as WikiPageTreeItem[];
      const summary: Record<string, string> = data?.pages_summary || {};
      setWikiData(tree, summary);
      if (cancelled || controller.signal.aborted) return;
      const stillThere = tree.some(p => p.id === activePageId);
      if (tree.length && (!activePageId || !stillThere)) setActivePage(tree[0].id);
    }).catch(err => {
      if ((err as any)?.name === 'AbortError') return;
      console.warn('fetchWiki error', err);
      if (!cancelled) setWikiData([], {});
    });
    return () => { cancelled = true; controller.abort(); };
  }, [effectiveId, setWikiData, setActivePage]);

  useEffect(() => {
    if (!effectiveId || !activePageId) return;
    let cancelled = false;
    const controller = new AbortController();
    setActivePageContent(null);
    fetchWikiPage(effectiveId, activePageId, controller.signal).then(data => {
      if (cancelled || controller.signal.aborted) return;
      setActivePageContent(data);
    }).catch(err => {
      if ((err as any)?.name === 'AbortError') return;
      console.warn('fetchWikiPage error', err);
      if (!cancelled) setActivePageContent(null);
    });
    return () => { cancelled = true; controller.abort(); };
  }, [effectiveId, activePageId, setActivePageContent]);

  useEffect(() => {
    const root = contentRef.current;
    if (!root) return;
    const els = Array.from(root.querySelectorAll('[data-section]')) as HTMLElement[];
    if (!els.length || !('IntersectionObserver' in window)) return;
    const obs = new IntersectionObserver(
      (entries) => { for (const e of entries) if (e.isIntersecting) setActiveSection((e.target as HTMLElement).dataset.section || null); },
      { root, rootMargin: '-20% 0px -70% 0px' }
    );
    els.forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, [activePageId, activePageContent]);

  const askQuestion = async (queryText?: string) => {
    const q = (queryText ?? qaQuestion).trim();
    if (!q || !effectiveId || qaLoading) return;
    setQaQuestion('');
    setQaError(null);
    setQaLoading(true);
    setRightTab('qa');
    try {
      const resp = await askWikiCopilot(effectiveId, q, activePageId || undefined);
      setQaHistory(prev => [...prev, {
        question: q,
        answer: resp.answer,
        citations: resp.citations || [],
        verdict: resp.verdict || 'VERIFIED_EVIDENCE',
      }]);
      setTimeout(() => qaScrollRef.current?.scrollTo({ top: 99999, behavior: 'smooth' }), 50);
    } catch (e: any) {
      setQaError(e?.message || 'Failed to get answer from DeepWiki AI');
    } finally {
      setQaLoading(false);
    }
  };

  const renderModeSwitcher = () => (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#11131a] border border-zinc-800">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setWikiMode('digest')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
            wikiMode === 'digest'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-slate-400 hover:text-white bg-zinc-800/60'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>GitIngest Code Context (Prompt Digest)</span>
        </button>
        <button
          onClick={() => setWikiMode('docs')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
            wikiMode === 'docs'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-slate-400 hover:text-white bg-zinc-800/60'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Architectural Living Wiki Docs</span>
        </button>
      </div>
      <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">GitIngest Engine</span>
    </div>
  );

  if (wikiMode === 'digest') {
    return (
      <div className="space-y-4">
        {renderModeSwitcher()}
        <GitIngestView />
      </div>
    );
  }

  if (!effectiveId) {
    return (
      <div className="space-y-4">
        {renderModeSwitcher()}
        <div className="dl-flex-center" style={{ minHeight: '40vh' }}>
          <GlassPanel className="p-6 text-center" style={{ maxWidth: '440px' }}>
            <BookOpen className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--dl-accent)' }} />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-1">DeepWiki Repository Living Docs</h2>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">
              Every wiki page is dynamically generated from AST symbols and Kùzu graph relationships with line-level evidence grounding.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => {
                  fetch('/api/wiki')
                    .then(r => r.ok ? r.json() : null)
                    .then(d => {
                      if (d?.analysis_run_id) setAnalysisId(d.analysis_run_id);
                      else setAnalysisId('run_d468fa7f8442');
                    })
                    .catch(() => setAnalysisId('run_d468fa7f8442'));
                }}
                className="dl-btn-primary px-4 py-2 text-xs font-bold"
              >
                Load Repository Living Wiki
              </button>
              <button
                onClick={() => setWikiMode('digest')}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white bg-zinc-800/50 rounded-lg"
              >
                Switch to GitIngest Code Digest
              </button>
            </div>
          </GlassPanel>
        </div>
      </div>
    );
  }

  if (loading && pageTree.length === 0) {
    return (
      <div className="space-y-4">
        <div className="dl-flex-gap-3">
          <BookOpen className="w-5 h-5" style={{ color: 'var(--dl-accent)' }} />
          <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color: 'var(--dl-text-dim)' }}>
            <span>Wiki</span><span style={{ color: 'var(--dl-text-muted)' }}>/</span><span className="text-slate-900 dark:text-white font-semibold">Generating…</span>
          </div>
        </div>
        <div className="space-y-3">
          {[0, 1, 2, 3].map(i => <WikiSectionSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  const tree: WikiPageTreeItem[] = pageTree || [];
  const grouped = groupByCategory(tree);
  const toggle = (cat: Category) => setOpenSections(prev => ({ ...prev, [cat]: !prev[cat] }));

  const flatPages = CATEGORY_ORDER.flatMap(cat => grouped[cat]);
  const activeIdx = flatPages.findIndex(p => p.id === activePageId);
  const prevPage = activeIdx > 0 ? flatPages[activeIdx - 1] : null;
  const nextPage = activeIdx >= 0 && activeIdx < flatPages.length - 1 ? flatPages[activeIdx + 1] : null;

  const searchResults = search.trim()
    ? tree.filter(p => p.title.toLowerCase().includes(search.toLowerCase()) || (pagesSummary[p.id] || '').toLowerCase().includes(search.toLowerCase()))
    : [];

  const goToPage = (pageId: string) => {
    setActivePage(pageId);
    contentRef.current?.scrollTo({ top: 0 });
  };

  const q = search.trim();
  const currentPageTitle = activePageContent?.title || flatPages.find(p => p.id === activePageId)?.title || 'Overview';

  return (
    <div className="space-y-4 dl-fade-in">
      {renderModeSwitcher()}
      {/* Sticky breadcrumb + controls */}
      <div className="sticky top-0 z-30 dl-panel p-3 rounded-sm">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="p-1.5 rounded-sm" style={{ background: 'var(--dl-accent-soft)', border: '1px solid var(--dl-accent)' }}>
            <BookOpen className="w-4 h-4" style={{ color: 'var(--dl-accent)' }} />
          </div>
          <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color: 'var(--dl-text-dim)' }}>
            <span>Wiki</span><span style={{ color: 'var(--dl-text-muted)' }}>/</span>
            <span className="text-slate-900 dark:text-white font-semibold">{currentPageTitle}</span>
          </div>

          {/* AI Provider Status Pill */}
          <div className="relative">
            <button
              onClick={() => setShowKeyHint(prev => !prev)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-sm text-[11px] font-mono border transition-colors"
              style={providerStatus?.configured
                ? { background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#10b981' }
                : { background: 'var(--dl-surface)', borderColor: 'var(--dl-panel-border)', color: 'var(--dl-text-dim)' }}
              title="Click to view LLM configuration info"
            >
              <Sparkles className="w-3 h-3" />
              <span>
                {providerStatus?.configured
                  ? `AI: ${providerStatus.provider.toUpperCase()} (${providerStatus.model})`
                  : 'AI: DETERMINISTIC OFFLINE'}
              </span>
              <HelpCircle className="w-3 h-3 opacity-60 ml-0.5" />
            </button>

            {showKeyHint && (
              <div
                className="absolute left-0 mt-2 z-50 p-4 rounded-sm w-80 text-left shadow-2xl font-mono"
                style={{ background: 'var(--dl-panel)', border: '1px solid var(--dl-panel-border)', boxShadow: '0 20px 50px rgba(0,0,0,0.8)' }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-black dark:text-white flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-[var(--dl-accent)]" /> AI Reasoning Setup
                  </span>
                  <button onClick={() => setShowKeyHint(false)} className="text-xs text-[var(--dl-text-muted)] hover:text-white">✕</button>
                </div>
                <p className="text-[11px] leading-relaxed" style={{ color: 'var(--dl-text-dim)' }}>
                  DevLensX uses hybrid intelligence: factual AST and Kùzu graphs + LLM generative synthesis.
                </p>
                <div className="mt-2.5 p-2 rounded-sm text-[10px] space-y-1" style={{ background: 'var(--dl-bg)', border: '1px solid var(--dl-panel-border)' }}>
                  <div className="text-[var(--dl-text-muted)]">Add to your root <code>.env</code>:</div>
                  <div className="text-[#10b981]">GEMINI_API_KEY=your_key</div>
                  <div className="text-[var(--dl-text-dim)]"># or OPENAI_API_KEY / GROQ_API_KEY</div>
                  <div className="text-[var(--dl-text-dim)]"># or OLLAMA_URL=http://localhost:11434</div>
                </div>
                <div className="mt-2 text-[10px]" style={{ color: 'var(--dl-text-muted)' }}>
                  Current Mode: <strong className="text-white">{providerStatus?.configured ? 'Active Frontier LLM' : 'Evidence Heuristics'}</strong>
                </div>
              </div>
            )}
          </div>

          {/* Quick Ask Wiki Button */}
          <button
            onClick={() => setRightTab(prev => prev === 'qa' ? 'toc' : 'qa')}
            className="dl-btn-primary px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 ml-auto sm:ml-0"
            style={rightTab === 'qa' ? { background: 'var(--dl-accent)', color: '#000' } : {}}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {rightTab === 'qa' ? 'Close Copilot' : 'Ask DeepWiki'}
          </button>

          {/* Search jump */}
          <div className="ml-auto relative w-full sm:w-64">
            <input
              value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Jump to page or entity…"
              aria-label="Search wiki pages"
              className="dl-input dl-input-mono w-full"
            />
            {q && (
              <div className="absolute right-0 mt-1 w-full rounded-sm z-50 max-h-64 overflow-y-auto" style={{ background: 'var(--dl-panel)', border: '1px solid var(--dl-panel-border)', boxShadow: '0 16px 48px -16px rgba(0,0,0,0.8)' }}>
                {searchResults.length === 0 && (
                  <div className="px-3 py-2 text-[11px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>No pages match &ldquo;{search}&rdquo;.</div>
                )}
                {searchResults.map(p => (
                  <button key={p.id} onClick={() => { goToPage(p.id); setSearch(''); }}
                    className="w-full text-left px-3 py-2 text-xs font-mono transition-colors"
                    style={{ color: 'var(--dl-text)' }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--dl-surface-hover)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}>
                    {p.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <p className="text-[11px] font-mono mt-2 flex items-center gap-2" style={{ color: 'var(--dl-text-muted)' }}>
          <GitCommit className="w-3 h-3" />
          {tree.length} pages &middot; {effectiveId}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: page tree */}
        <aside className="lg:col-span-3 dl-panel p-3 rounded-sm font-mono text-xs space-y-2 max-h-[820px] overflow-y-auto">
          <div className="dl-panel-label px-2 pb-1 border-b" style={{ borderColor: 'var(--dl-panel-border)' }}>Pages</div>
          <div className="space-y-1">
            {CATEGORY_ORDER.map(cat => {
              const items = grouped[cat];
              if (!items.length) return null;
              const Icon = CATEGORY_ICONS[cat];
              const isOpen = openSections[cat];
              return (
                <div key={cat}>
                  <button onClick={() => toggle(cat)} className="w-full text-left px-2 py-1.5 rounded-sm flex items-center gap-2 transition-colors" style={{ color: 'var(--dl-text)' }}>
                    <Icon className="w-3.5 h-3.5 text-[var(--dl-accent)]" />
                    <span className="flex-1">{cat} <span className="text-[10px]" style={{ color: 'var(--dl-text-muted)' }}>({items.length})</span></span>
                    {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </button>
                  {isOpen && (
                    <div className="ml-2 pl-2 border-l space-y-0.5 mt-1" style={{ borderColor: 'var(--dl-panel-border)' }}>
                      {items.map(item => (
                        <button key={item.id} onClick={() => setActivePage(item.id)}
                          className="w-full text-left px-2 py-1 rounded-sm text-[11px] transition-colors"
                          style={activePageId === item.id
                            ? { background: 'var(--dl-accent-soft)', color: 'var(--dl-accent)', borderLeft: '2px solid var(--dl-accent)', fontWeight: 600 }
                            : { color: 'var(--dl-text-dim)' }}>
                          {item.title}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>

        {/* Center: reading column */}
        <main ref={contentRef} className="lg:col-span-6 dl-panel p-5 rounded-sm space-y-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          {!activePageContent ? (
            <div className="text-center py-12 text-xs font-mono" style={{ color: 'var(--dl-text-dim)' }}>Select a page from the left to read.</div>
          ) : (
            <div className="mx-auto" style={{ maxWidth: '720px' }}>
              <div className="border-b pb-3 flex items-center justify-between gap-3" style={{ borderColor: 'var(--dl-panel-border)' }}>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">{activePageContent.title}</h2>
                <Badge variant="finding-perf" size="sm">{activePageContent.type || activePageContent.status || 'VERIFIED'}</Badge>
              </div>

              {activePageContent.summary && (
                <p className="text-xs font-mono text-slate-600 dark:text-slate-300 mt-2.5 leading-relaxed">
                  {activePageContent.summary}
                </p>
              )}
              {activePageContent.purpose && !activePageContent.summary && (
                <p className="text-xs font-mono text-slate-600 dark:text-slate-300 mt-2.5 leading-relaxed">
                  {activePageContent.purpose}
                </p>
              )}

              {/* DeepWiki Signature Context: Relevant Source Files */}
              {activePageContent.citations && activePageContent.citations.length > 0 && (
                <details className="mt-3.5 mb-5 rounded border border-neutral-200 dark:border-zinc-800 bg-neutral-50 dark:bg-[#121318] p-3 text-xs font-mono">
                  <summary className="cursor-pointer font-bold text-neutral-800 dark:text-zinc-200 hover:text-black dark:hover:text-white select-none flex items-center justify-between">
                    <span>Relevant source files ({activePageContent.citations.length})</span>
                    <span className="text-[10px] text-neutral-400 dark:text-zinc-500 font-normal">Grounded Context</span>
                  </summary>
                  <div className="mt-2.5 pt-2 border-t border-neutral-200 dark:border-zinc-800 space-y-1 text-[11px]">
                    <p className="text-neutral-500 dark:text-zinc-400 mb-1.5">
                      The following source files and AST symbols were used as context for generating this documentation:
                    </p>
                    {activePageContent.citations.slice(0, 15).map((c: any, i: number) => {
                      const span = c.line_start && c.line_end ? `:${c.line_start}-${c.line_end}` : '';
                      const file = c.file || c.symbol || 'source';
                      return (
                        <div key={i} className="flex items-center gap-2 text-neutral-700 dark:text-zinc-300">
                          <span className="text-neutral-400 dark:text-zinc-500">•</span>
                          <span className="font-semibold text-neutral-900 dark:text-zinc-100">{file}{span}</span>
                          {c.symbol && <span className="text-neutral-400 dark:text-zinc-500">({c.symbol})</span>}
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}

              {activePageContent.verification_summary && (
                <div className="flex items-center gap-2 mt-2 text-[11px] font-mono">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                    ✓ {activePageContent.verification_summary.verified || 0} Claims Verified
                  </span>
                  {activePageContent.verification_summary.insufficient_evidence > 0 && (
                    <span className="text-rose-500 font-bold">
                      · {activePageContent.verification_summary.insufficient_evidence} Fail-Closed
                    </span>
                  )}
                </div>
              )}

              {/* Executive Stats Card on Overview Page */}
              {(activePageId === 'overview' || activePageContent?.type === 'overview') && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
                  <div className="p-2.5 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>MODULE PAGES</div>
                    <div className="text-xs font-bold font-mono text-black dark:text-white mt-0.5">{tree.length} Generated</div>
                  </div>
                  <div className="p-2.5 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>AI REASONING</div>
                    <div className="text-xs font-bold font-mono mt-0.5" style={{ color: providerStatus?.configured ? '#10b981' : 'var(--dl-accent)' }}>
                      {providerStatus?.configured ? providerStatus.provider.toUpperCase() : 'EVIDENCE'}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>DIAGRAMS</div>
                    <div className="text-xs font-bold font-mono text-black dark:text-white mt-0.5">AST + MERMAID</div>
                  </div>
                  <div className="p-2.5 rounded-sm" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>CONTRACT</div>
                    <div className="text-xs font-bold font-mono text-[var(--dl-accent)] mt-0.5">EVIDENCE-FIRST</div>
                  </div>
                </div>
              )}

              <div className="space-y-6 mt-4">
                {(activePageContent.sections || []).map((sec: any, idx: number) => (
                  <SectionView key={idx} section={sec} idx={idx} pagesSummary={pagesSummary} pageTree={tree} onNavigate={goToPage} onExpandDiagram={setExpandedDiagram} />
                ))}
              </div>

              {activePageContent.mermaid && (
                <div className="rounded-sm p-3 mt-6" style={{ background: 'var(--dl-bg)', border: '1px solid var(--dl-panel-border)' }}>
                  <div className="dl-panel-label mb-2 flex items-center gap-1.5"><FileCode className="w-3.5 h-3.5" />Mermaid &mdash; {activePageContent.title}</div>
                  <MermaidBlock code={activePageContent.mermaid} />
                  <button onClick={() => setExpandedDiagram(activePageContent.mermaid)} className="mt-1 text-[11px] font-mono underline underline-offset-2 flex items-center gap-1.5" style={{ color: 'var(--dl-accent)' }}>
                    <FileCode className="w-3.5 h-3.5" /> Expand diagram
                  </button>
                </div>
              )}

              <nav className="flex items-center justify-between pt-5 mt-6 border-t" style={{ borderColor: 'var(--dl-panel-border)' }} aria-label="Page navigation">
                {prevPage ? (
                  <button onClick={() => goToPage(prevPage.id)} className="dl-btn-ghost px-3 py-1.5 text-xs font-mono flex items-center gap-1.5">
                    <ArrowRight className="w-3.5 h-3.5 rotate-180" /> {prevPage.title}
                  </button>
                ) : <span />}
                {nextPage ? (
                  <button onClick={() => goToPage(nextPage.id)} className="dl-btn-ghost px-3 py-1.5 text-xs font-mono flex items-center gap-1.5">
                    {nextPage.title} <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                ) : <span />}
              </nav>
            </div>
          )}
        </main>

        {/* Right: segmented sidebar (Sections vs Ask Copilot) */}
        <aside className="lg:col-span-3">
          <div className="sticky top-24 dl-panel p-3 rounded-sm space-y-3 max-h-[820px] flex flex-col">
            <div className="flex border-b pb-1" style={{ borderColor: 'var(--dl-panel-border)' }}>
              <button
                onClick={() => setRightTab('toc')}
                className="flex-1 py-1.5 text-xs font-mono text-center transition-colors"
                style={rightTab === 'toc'
                  ? { borderBottom: '2px solid var(--dl-accent)', color: 'var(--dl-accent)', fontWeight: 600 }
                  : { color: 'var(--dl-text-dim)' }}
              >
                Sections
              </button>
              <button
                onClick={() => setRightTab('qa')}
                className="flex-1 py-1.5 text-xs font-mono text-center flex items-center justify-center gap-1.5 transition-colors"
                style={rightTab === 'qa'
                  ? { borderBottom: '2px solid var(--dl-accent)', color: 'var(--dl-accent)', fontWeight: 600 }
                  : { color: 'var(--dl-text-dim)' }}
              >
                <Sparkles className="w-3 h-3" />
                Ask Copilot
              </button>
            </div>

            {rightTab === 'toc' ? (
              <div className="space-y-2 overflow-y-auto flex-1">
                <div className="dl-panel-label mb-2">On This Page</div>
                {(activePageContent?.sections || []).length === 0 ? (
                  <div className="text-[11px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>No sections in this page.</div>
                ) : (
                  <div className="space-y-0.5">
                    {(activePageContent?.sections || []).map((sec: any, idx: number) => {
                      const raw = String(sec.heading || `Section ${idx + 1}`);
                      const label = cleanHeading(raw);
                      const isActive = activeSection === label || activeSection === raw;
                      return (
                        <button key={idx}
                          onClick={() => { const el = contentRef.current?.querySelector(`[data-section="${CSS.escape(label)}"]`) || contentRef.current?.querySelector(`[data-section="${CSS.escape(raw)}"]`); el?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
                          className="w-full text-left px-2 py-1 rounded-sm text-[11px] font-mono transition-colors truncate"
                          style={isActive ? { color: 'var(--dl-accent)', background: 'var(--dl-accent-soft)' } : { color: 'var(--dl-text-dim)' }}>
                          {label}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              /* DeepWiki AI Copilot Q&A Panel */
              <div className="space-y-3 flex-1 flex flex-col min-h-[380px]">
                <div className="p-2 rounded-sm text-[11px] font-mono flex items-center gap-2" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)' }}>
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-900 dark:text-white" />
                  <span className="truncate" style={{ color: 'var(--dl-text-dim)' }}>
                    Context: <strong className="text-black dark:text-white">{currentPageTitle}</strong>
                  </span>
                </div>

                {/* Quick suggestion pills */}
                <div className="space-y-1">
                  <div className="text-[10px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>SUGGESTED REPO QUERIES:</div>
                  <div className="flex flex-wrap gap-1">
                    {[
                      'What is this repository about and what does it do?',
                      'Explain the architecture and main workflows',
                      'Trace request flow from controller to database',
                      'What are the security risks or validation gaps?',
                    ].map(pill => (
                      <button
                        key={pill}
                        onClick={() => askQuestion(pill)}
                        className="text-[10px] font-mono px-2 py-1 rounded-sm text-left transition-colors border"
                        style={{ background: 'var(--dl-bg)', borderColor: 'var(--dl-panel-border)', color: 'var(--dl-text-dim)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--dl-accent)'; e.currentTarget.style.color = 'var(--dl-text-strong)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--dl-panel-border)'; e.currentTarget.style.color = 'var(--dl-text-dim)'; }}
                      >
                        {pill}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Chat message history */}
                <div ref={qaScrollRef} className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs font-mono max-h-[360px]">
                  {qaHistory.length === 0 && !qaLoading && (
                    <div className="text-center py-8 text-[11px]" style={{ color: 'var(--dl-text-muted)' }}>
                      Ask anything about this repository or module to receive grounded AI answers backed by AST code citations.
                    </div>
                  )}

                  {qaHistory.map((h, i) => (
                    <div key={i} className="space-y-1.5">
                      <div className="p-2 rounded-sm text-[11px]" style={{ background: 'var(--dl-surface)', border: '1px solid var(--dl-panel-border)', color: 'var(--dl-accent)' }}>
                        <strong>Q:</strong> {h.question}
                      </div>
                      <div className="p-2.5 rounded-sm text-[11px] leading-relaxed space-y-2" style={{ background: 'var(--dl-bg)', border: '1px solid var(--dl-panel-border)' }}>
                        <div className="whitespace-pre-wrap text-black dark:text-gray-200">{h.answer}</div>
                        {h.citations && h.citations.length > 0 && (
                          <div className="pt-1.5 border-t border-gray-800 space-y-1">
                            <div className="text-[10px] text-[var(--dl-text-muted)]">CITATIONS:</div>
                            {h.citations.map((c, ci) => (
                              <div key={ci} className="text-[10px] text-zinc-900 dark:text-zinc-100 font-mono truncate">
                                🔗 {c}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {qaLoading && (
                    <div className="p-3 rounded-sm flex items-center gap-2 text-xs" style={{ background: 'var(--dl-surface)' }}>
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--dl-accent)]" />
                      <span style={{ color: 'var(--dl-text-dim)' }}>Synthesizing answer from codebase evidence…</span>
                    </div>
                  )}

                  {qaError && (
                    <div className="p-2 rounded-sm text-xs" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
                      {qaError}
                    </div>
                  )}
                </div>

                {/* Input form */}
                <form
                  onSubmit={(e) => { e.preventDefault(); askQuestion(); }}
                  className="pt-2 border-t flex gap-1.5"
                  style={{ borderColor: 'var(--dl-panel-border)' }}
                >
                  <input
                    value={qaQuestion}
                    onChange={(e) => setQaQuestion(e.target.value)}
                    placeholder="Ask about this repo or page…"
                    className="dl-input dl-input-mono text-xs flex-1"
                    disabled={qaLoading}
                  />
                  <button
                    type="submit"
                    disabled={qaLoading || !qaQuestion.trim()}
                    className="dl-btn-primary px-3 py-1.5 flex items-center justify-center"
                    aria-label="Send question"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </form>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Expanded diagram modal */}
      {expandedDiagram && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6" style={{ background: 'rgba(0,0,0,0.8)' }} onClick={() => setExpandedDiagram(null)} role="dialog" aria-label="Expanded diagram">
          <div className="dl-panel p-5 rounded-sm max-w-5xl w-full max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <span className="dl-panel-label">Diagram</span>
              <button onClick={() => setExpandedDiagram(null)} className="dl-btn-ghost px-3 py-1 text-xs font-mono" aria-label="Close expanded diagram">Close ✕</button>
            </div>
            <MermaidBlock code={expandedDiagram} />
          </div>
        </div>
      )}
    </div>
  );
};
