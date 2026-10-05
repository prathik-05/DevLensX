import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { getPageByPath } from './pages/registry';
import { useAppStore } from './store';
import { useWorkspaceContext } from './workspaceContext';

const OverviewView = lazy(() => import('./components/OverviewView').then(m => ({ default: m.OverviewView })));
const WikiView = lazy(() => import('./components/WikiView').then(m => ({ default: m.WikiView })));
const CodemapView = lazy(() => import('./components/CodemapView').then(m => ({ default: m.CodemapView })));
const ExplorerView = lazy(() => import('./components/ExplorerView').then(m => ({ default: m.ExplorerView })));
const ArchitectureView = lazy(() => import('./components/ArchitectureView').then(m => ({ default: m.ArchitectureView })));
const AIAssistantView = lazy(() => import('./components/AIAssistantView').then(m => ({ default: m.AIAssistantView })));
const ReviewsView = lazy(() => import('./components/ReviewsView').then(m => ({ default: m.ReviewsView })));
const EvaluationView = lazy(() => import('./components/EvaluationView').then(m => ({ default: m.EvaluationView })));
const ChangeImpactView = lazy(() => import('./components/ChangeImpactView').then(m => ({ default: m.ChangeImpactView })));
const SettingsView = lazy(() => import('./components/SettingsView').then(m => ({ default: m.SettingsView })));
const CodeTurtleView = lazy(() => import('./components/CodeTurtleView').then(m => ({ default: m.CodeTurtleView })));
const CodeRabbitView = CodeTurtleView;
const DebugView = lazy(() => import('./components/DebugView').then(m => ({ default: m.DebugView })));
const GovernanceView = lazy(() => import('./components/GovernanceView').then(m => ({ default: m.GovernanceView })));
const IngestView = lazy(() => import('./components/IngestView').then(m => ({ default: m.IngestView })));

const LandingPage = lazy(() => import('./components/LandingPage').then(m => ({ default: m.LandingPage })));

const pageComponents: Record<string, React.ComponentType<any>> = {
  overview: OverviewView,
  ingest: IngestView,
  wiki: WikiView,
  codemap: CodemapView,
  explorer: ExplorerView,
  architecture: ArchitectureView,
  governance: GovernanceView,
  'ai-assistant': AIAssistantView,
  reviews: ReviewsView,
  evaluation: EvaluationView,
  changelog: ChangeImpactView,
  'change-impact': ChangeImpactView,
  settings: SettingsView,
  'code-turtle': CodeTurtleView,
  'code-rabbit': CodeRabbitView,
  debug: DebugView,
};

function PageWrapper({ pageId }: { pageId: string }) {
  const Component = pageComponents[pageId];

  if (!Component) {
    return (
      <div className="dl-panel p-6 dl-flex-center" style={{ minHeight: '400px' }}>
        <div className="text-center">
          <span className="text-4xl mb-3 block">📄</span>
          <h2 className="text-lg font-bold text-black dark:text-white mb-1">Page Not Implemented</h2>
          <p className="text-sm" style={{ color: 'var(--dl-text-dim)' }}>{pageId}</p>
        </div>
      </div>
    );
  }

  return <Component />;
}

function LoadingFallback() {
  return (
    <div className="dl-flex-center" style={{ minHeight: '300px' }}>
      <div className="dl-flex-gap-3">
        <span className="dl-skeleton-line" style={{ width: '120px' }} />
        <span className="dl-caret" style={{ fontFamily: 'var(--dl-font-mono)', color: 'var(--dl-accent)' }}>awaiting analysis</span>
      </div>
    </div>
  );
}

/** Copies the latest backend analysis identity into the workspace context
 * so Wiki/Codemap/Reviews resolve against the analyzed snapshot. */
const WorkspaceSync: React.FC = () => {
  const analysisData = useAppStore(s => s.analysisData);
  const { setContext } = useWorkspaceContext();
  useEffect(() => {
    if (analysisData?.analysis_run_id) {
      setContext({
        repository_id: analysisData.repository ?? '',
        analysis_run_id: analysisData.analysis_run_id,
        commit_hash: null,
      });
    }
  }, [analysisData, setContext]);
  return null;
};

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { repoPath } = useAppStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activePage, setActivePage] = useState(() => {
    const path = location.pathname.slice(1) || 'overview';
    return getPageByPath(`/${path}`)?.id || 'overview';
  });

  useEffect(() => {
    const path = location.pathname.slice(1) || 'overview';
    const page = getPageByPath(`/${path}`);
    if (page) setActivePage(page.id);
  }, [location.pathname]);

  const handleNavigate = (pageId: string) => {
    const page = getPageByPath(`/${pageId}`);
    const target = page ?? { path: `/${pageId}` };
    navigate(target.path);
    setActivePage(pageId);
  };

  useEffect(() => {
    if (repoPath.trim()) {
      window.dispatchEvent(new CustomEvent('devlensx:repo-change', { detail: { path: repoPath } }));
    }
  }, [repoPath]);

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--dl-bg)', color: 'var(--dl-text)' }}>
      <WorkspaceSync />
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
        activePage={activePage}
        onNavigate={handleNavigate}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activePage={activePage}
          onNavigate={handleNavigate}
          onToggleSidebar={() => setSidebarCollapsed(c => !c)}
          sidebarCollapsed={sidebarCollapsed}
        />

        <main className="flex-1 p-4 overflow-auto" style={{ background: 'var(--dl-bg)' }}>
          <Suspense fallback={<LoadingFallback />}>
            <PageWrapper pageId={activePage} />
          </Suspense>
        </main>
      </div>
    </div>
  );
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/overview" element={<AppLayout />} />
      <Route path="/ingest" element={<AppLayout />} />
      <Route path="/wiki" element={<AppLayout />} />
      <Route path="/codemap" element={<AppLayout />} />
      <Route path="/explorer" element={<AppLayout />} />
      <Route path="/guided-tours" element={<Navigate to="/explorer" replace />} />
      <Route path="/architecture" element={<AppLayout />} />
      <Route path="/governance" element={<AppLayout />} />
      <Route path="/ai-assistant" element={<AppLayout />} />
      <Route path="/reviews" element={<AppLayout />} />
      <Route path="/evaluation" element={<AppLayout />} />
      <Route path="/changelog" element={<AppLayout />} />
      <Route path="/change-impact" element={<AppLayout />} />
      <Route path="/code-turtle" element={<AppLayout />} />
      <Route path="/code-rabbit" element={<AppLayout />} />
      <Route path="/debug" element={<AppLayout />} />
      <Route path="/settings" element={<AppLayout />} />
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  );
};