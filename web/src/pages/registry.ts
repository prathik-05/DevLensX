/**
 * DevLensX Page Registry — Single source of truth for all views.
 * Adding a new view = add one entry here. Nav, Router, Command Palette all read from this.
 */

import type { ComponentType } from 'react';
import {
  Home,
  BookOpen,
  Map,
  Search,
  GitBranch,
  Shield,
  Settings,
  Brain,
  Terminal,
  Zap,
  AlertTriangle,
  GitPullRequest,
  Bot,
  Bug,
  FileText
} from 'lucide-react';

export type NavGroup = 'repository' | 'understand' | 'explore' | 'ai-assistant' | 'code-review' | 'config';

export interface PageRegistryEntry {
  id: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  path: string;
  component: ComponentType<any> | (() => Promise<{ default: ComponentType<any> }>);
  group: NavGroup;
  description: string;
  keywords: string[];
  enabled?: boolean;
  badge?: string;
}

export const pageRegistry: PageRegistryEntry[] = [
  // 1. REPOSITORY
  {
    id: 'overview',
    label: 'Overview',
    icon: Home,
    path: '/overview',
    component: () => import('../components/OverviewView').then(m => ({ default: m.OverviewView })),
    group: 'repository',
    description: 'Repository health, metrics & intelligence score',
    keywords: ['health', 'score', 'metrics', 'intelligence', 'summary', 'setup', 'features'],
  },
  {
    id: 'ingest',
    label: 'Repo Ingest',
    icon: FileText,
    path: '/ingest',
    component: () => import('../components/IngestView').then(m => ({ default: m.IngestView })),
    group: 'repository',
    description: 'GitIngest prompt digest, directory tree, live token count & single-click analysis',
    keywords: ['ingest', 'gitingest', 'digest', 'prompt', 'llm', 'token', 'context'],
    badge: 'LLM',
  },

  // 2. UNDERSTAND
  {
    id: 'wiki',
    label: 'DeepWiki',
    icon: Brain,
    path: '/wiki',
    component: () => import('../components/WikiView').then(m => ({ default: m.WikiView })),
    group: 'understand',
    description: 'Human-friendly architecture explanations & deep-dive docs',
    keywords: ['documentation', 'architecture', 'explanation', 'reasoning', 'deep-dive', 'wiki'],
    badge: 'DOCS',
  },
  {
    id: 'codemap',
    label: 'Code Map',
    icon: Map,
    path: '/codemap',
    component: () => import('../components/CodemapView').then(m => ({ default: m.CodemapView })),
    group: 'understand',
    description: 'Interactive codebase tour with blast-radius ranking',
    keywords: ['tour', 'blast-radius', 'ranking', 'components', 'navigation'],
  },
  {
    id: 'architecture',
    label: 'Architecture',
    icon: GitBranch,
    path: '/architecture',
    component: () => import('../components/ArchitectureView').then(m => ({ default: m.ArchitectureView })),
    group: 'understand',
    description: 'System dependency graphs, layer analysis & patterns',
    keywords: ['dependency', 'graph', 'layers', 'patterns', 'coupling'],
  },

  // 3. EXPLORE
  {
    id: 'explorer',
    label: 'Explorer',
    icon: Search,
    path: '/explorer',
    component: () => import('../components/ExplorerView').then(m => ({ default: m.ExplorerView })),
    group: 'explore',
    description: 'Browse symbols, files, dependencies & call graphs',
    keywords: ['symbols', 'files', 'dependencies', 'call-graph', 'browse'],
  },
  // 4. AI ASSISTANT
  {
    id: 'ai-assistant',
    label: 'AI Assistant',
    icon: Bot,
    path: '/ai-assistant',
    component: () => import('../components/AIAssistantView').then(m => ({ default: m.AIAssistantView })),
    group: 'ai-assistant',
    description: 'ChatGPT/Claude for repo, Where Should I Edit?, and Concept Explanations',
    keywords: ['assistant', 'copilot', 'chat', 'where-to-edit', 'concepts', 'gemini', 'gpt'],
    badge: 'AI',
  },

  // 5. CODE REVIEW
  {
    id: 'code-turtle',
    label: 'Code Turtle',
    icon: GitPullRequest,
    path: '/code-turtle',
    component: () => import('../components/CodeTurtleView').then(m => ({ default: m.CodeTurtleView })),
    group: 'code-review',
    description: 'Senior PR code review, live code editor, 1-click committable fixes',
    keywords: ['review', 'diff', 'pr', 'turtle', 'codeturtle', 'editor', 'security'],
    badge: 'SENIOR',
  },
  {
    id: 'reviews',
    label: 'Findings & Audit',
    icon: Shield,
    path: '/reviews',
    component: () => import('../components/ReviewsView').then(m => ({ default: m.ReviewsView })),
    group: 'code-review',
    description: 'Security findings, engineering recommendations & PR audit',
    keywords: ['security', 'findings', 'recommendations', 'audit', 'pr'],
  },
  {
    id: 'changelog',
    label: 'Change Impact',
    icon: AlertTriangle,
    path: '/changelog',
    component: () => import('../components/ChangeImpactView').then(m => ({ default: m.ChangeImpactView })),
    group: 'code-review',
    description: '4-tier blast-radius cascade & verification checklist',
    keywords: ['blast-radius', 'migration', 'risk', 'impact', 'change', 'cascade'],
  },
  {
    id: 'debug',
    label: 'Debug Center',
    icon: Bug,
    path: '/debug',
    component: () => import('../components/DebugView').then(m => ({ default: m.DebugView })),
    group: 'code-review',
    description: 'Ground stack traces against AST class nodes & Kuzu dependency graph',
    keywords: ['debug', 'stacktrace', 'exception', 'root-cause', 'error', 'crash'],
  },

  // CONFIG
  {
    id: 'evaluation',
    label: 'Evaluation Lab',
    icon: Zap,
    path: '/evaluation',
    component: () => import('../components/EvaluationView').then(m => ({ default: m.EvaluationView })),
    group: 'config',
    description: 'Golden eval, grounding tests & regression benchmarks',
    keywords: ['evaluation', 'golden', 'grounding', 'benchmarks', 'regression'],
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    path: '/settings',
    component: () => import('../components/SettingsView').then(m => ({ default: m.SettingsView })),
    group: 'config',
    description: 'Configuration, API keys, analysis options & integrations',
    keywords: ['config', 'api', 'keys', 'options', 'integrations'],
  },
];

export const navGroups: { id: NavGroup; label: string; order: number }[] = [
  { id: 'repository', label: '1. REPOSITORY', order: 1 },
  { id: 'understand', label: '2. UNDERSTAND', order: 2 },
  { id: 'explore', label: '3. EXPLORE', order: 3 },
  { id: 'ai-assistant', label: '4. AI ASSISTANT', order: 4 },
  { id: 'code-review', label: '5. CODE REVIEW', order: 5 },
  { id: 'config', label: 'SYSTEM / CONFIG', order: 6 },
];

/**
 * Get all enabled pages for navigation
 */
export function getNavPages(): PageRegistryEntry[] {
  return pageRegistry
    .filter(p => p.enabled !== false)
    .sort((a, b) => {
      const ga = navGroups.find(g => g.id === a.group)?.order ?? 99;
      const gb = navGroups.find(g => g.id === b.group)?.order ?? 99;
      return ga - gb || a.label.localeCompare(b.label);
    });
}

/**
 * Get page by ID
 */
export function getPage(id: string): PageRegistryEntry | undefined {
  return pageRegistry.find(p => p.id === id);
}

/**
 * Get page by path
 */
export function getPageByPath(path: string): PageRegistryEntry | undefined {
  return pageRegistry.find(p => p.path === path);
}

/**
 * Search pages for command palette
 */
export function searchPages(query: string): PageRegistryEntry[] {
  const q = query.toLowerCase().trim();
  if (!q) return getNavPages();
  return getNavPages().filter(p =>
    p.id.toLowerCase().includes(q) ||
    p.label.toLowerCase().includes(q) ||
    p.description.toLowerCase().includes(q) ||
    p.keywords.some(k => k.toLowerCase().includes(q))
  );
}

/**
 * Get all command palette actions (pages + custom actions)
 */
export function getCommandActions(): Array<{
  id: string;
  label: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  action: 'navigate' | 'custom';
  payload?: any;
  keywords: string[];
}> {
  const pageActions = getNavPages().map(p => ({
    id: `nav:${p.id}`,
    label: p.label,
    description: p.description,
    icon: p.icon,
    action: 'navigate' as const,
    payload: p.path,
    keywords: ['go to', 'open', 'navigate', ...p.keywords],
  }));

  const customActions = [
    {
      id: 'cmd:analyze',
      label: 'Analyze Repository',
      description: 'Run full analysis on current repository',
      icon: Terminal,
      action: 'custom' as const,
      payload: { type: 'analyze' },
      keywords: ['analyze', 'run', 'scan', 'repository', 'codebase'],
    },
    {
      id: 'cmd:switch-repo',
      label: 'Switch Repository',
      description: 'Change target repository or upload zip',
      icon: Home,
      action: 'custom' as const,
      payload: { type: 'switch-repo' },
      keywords: ['switch', 'change', 'repository', 'repo', 'upload'],
    },
    {
      id: 'cmd:export-wiki',
      label: 'Export Wiki',
      description: 'Export generated wiki as Markdown/HTML',
      icon: BookOpen,
      action: 'custom' as const,
      payload: { type: 'export-wiki' },
      keywords: ['export', 'wiki', 'markdown', 'html', 'download'],
    },
    {
      id: 'cmd:code-review',
      label: 'Code Review (Code Turtle)',
      description: 'AI-powered code review on current diff',
      icon: Shield,
      action: 'custom' as const,
      payload: { type: 'code-review' },
      keywords: ['review', 'code', 'turtle', 'codeturtle', 'ai', 'diff', 'pr'],
    },
    {
      id: 'cmd:clear-cache',
      label: 'Clear Cache',
      description: 'Invalidate all cached analyses & wiki data',
      icon: AlertTriangle,
      action: 'custom' as const,
      payload: { type: 'clear-cache' },
      keywords: ['clear', 'cache', 'invalidate', 'reset'],
    },
    {
      id: 'cmd:repo-ingest',
      label: 'GitIngest Repo Context Bundler',
      description: 'Convert Git repo or folder into single prompt digest with token counter',
      icon: FileText,
      action: 'navigate' as const,
      payload: '/ingest',
      keywords: ['gitingest', 'ingest', 'digest', 'bundle', 'tokens', 'llm prompt', 'context'],
    },
  ];

  return [...pageActions, ...customActions];
}