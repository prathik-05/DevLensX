/**
 * DevLensX Page Registry — Single source of truth for all views.
 * Adding a new view = add one entry here. Nav, Router, Command Palette all read from this.
 */

import type { ComponentType } from 'react';
import {
  Home,
  BookOpen,
  Search,
  Settings,
  Brain,
  AlertTriangle,
  GitPullRequest,
  Bot,
  FileText,
  Shield,
  Terminal
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
    keywords: ['health', 'score', 'metrics', 'intelligence', 'summary'],
  },
  {
    id: 'ingest',
    label: 'Repository Ingest',
    icon: FileText,
    path: '/ingest',
    component: () => import('../components/IngestView').then(m => ({ default: m.IngestView })),
    group: 'repository',
    description: 'Import Git repository URL or ZIP archive, track parsing & analysis',
    keywords: ['ingest', 'clone', 'zip', 'upload'],
    badge: 'CORE',
  },

  // 2. EXPLORE & INSPECT
  {
    id: 'explorer',
    label: 'Explorer',
    icon: Search,
    path: '/explorer',
    component: () => import('../components/ExplorerView').then(m => ({ default: m.ExplorerView })),
    group: 'explore',
    description: 'Real source files, AST symbols, references, callers & line-level evidence',
    keywords: ['symbols', 'files', 'dependencies', 'call-graph', 'source', 'ast'],
  },

  // 3. LIVING ARCHITECTURE
  {
    id: 'wiki',
    label: 'DeepWiki',
    icon: Brain,
    path: '/wiki',
    component: () => import('../components/WikiView').then(m => ({ default: m.WikiView })),
    group: 'understand',
    description: 'Grounded architectural living documentation & component layer flow',
    keywords: ['documentation', 'architecture', 'explanation', 'layer', 'wiki'],
    badge: 'DOCS',
  },

  // 4. IMPACT & SECURITY
  {
    id: 'change-impact',
    label: 'Impact & Security',
    icon: AlertTriangle,
    path: '/change-impact',
    component: () => import('../components/ChangeImpactView').then(m => ({ default: m.ChangeImpactView })),
    group: 'code-review',
    description: 'Dependency change impact blast-radius cascade & verified security findings',
    keywords: ['impact', 'blast-radius', 'security', 'findings', 'cascade', 'audit'],
    badge: 'AUDIT',
  },

  // 5. AI ASSISTANT
  {
    id: 'ai-assistant',
    label: 'AI Assistant',
    icon: Bot,
    path: '/ai-assistant',
    component: () => import('../components/AIAssistantView').then(m => ({ default: m.AIAssistantView })),
    group: 'ai-assistant',
    description: 'Repository-grounded Q&A, Where Should I Edit?, and Concept Explanations',
    keywords: ['assistant', 'copilot', 'chat', 'where-to-edit', 'concepts'],
    badge: 'AI',
  },

  // 6. CODE TURTLE (PR REVIEW)
  {
    id: 'code-turtle',
    label: 'Code Turtle',
    icon: GitPullRequest,
    path: '/code-turtle',
    component: () => import('../components/CodeTurtleView').then(m => ({ default: m.CodeTurtleView })),
    group: 'code-review',
    description: 'Seeded PR bug scenarios & live diff review with proposal safety',
    keywords: ['review', 'diff', 'pr', 'turtle', 'codeturtle'],
    badge: 'DEMO/LIVE',
  },

  // SYSTEM
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    path: '/settings',
    component: () => import('../components/SettingsView').then(m => ({ default: m.SettingsView })),
    group: 'config',
    description: 'Configuration, LLM API keys & system options',
    keywords: ['config', 'api', 'keys', 'options'],
  },
];

export const navGroups: { id: NavGroup; label: string; order: number }[] = [
  { id: 'repository', label: '1. REPOSITORY', order: 1 },
  { id: 'explore', label: '2. EXPLORE', order: 2 },
  { id: 'understand', label: '3. UNDERSTAND', order: 3 },
  { id: 'code-review', label: '4. IMPACT & AUDIT', order: 4 },
  { id: 'ai-assistant', label: '5. AI ASSISTANT', order: 5 },
  { id: 'config', label: 'SYSTEM', order: 6 },
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