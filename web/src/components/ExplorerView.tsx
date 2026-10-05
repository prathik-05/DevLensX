import React from 'react';
import { useAppStore } from '../store';
import { ExplorerPage } from './ExplorerPage';
import { GlassPanel } from './GlassPanel';
import { Globe } from 'lucide-react';

export const ExplorerView: React.FC = () => {
  const data = useAppStore(s => s.analysisData);

  if (!data || !data.analysis_run_id) {
    return (
      <div className="dl-flex-center" style={{ minHeight: '50vh' }}>
        <GlassPanel className="p-6 text-center max-w-md">
          <Globe className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--dl-accent)' }} />
          <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--dl-text)' }}>No Analysis Available</h2>
          <p className="text-sm font-mono" style={{ color: 'var(--dl-text-dim)' }}>
            Analyze a repository from the sidebar or header to explore codebase files, inspect AST methods, and query AI code intelligence.
          </p>
        </GlassPanel>
      </div>
    );
  }

  return <ExplorerPage data={data} />;
};

