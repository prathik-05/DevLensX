import React from 'react';
import { useAppStore } from '../store';
import { ArchitecturePage } from './ArchitecturePage';
import { GlassPanel } from './GlassPanel';
import { Compass } from 'lucide-react';

export const ArchitectureView: React.FC = () => {
  const data = useAppStore(s => s.analysisData);

  if (!data || !data.analysis_run_id) {
    return (
      <div className="dl-flex-center" style={{ minHeight: '50vh' }}>
        <GlassPanel className="p-6 text-center max-w-md">
          <Compass className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--dl-accent)' }} />
          <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--dl-text)' }}>No Analysis Available</h2>
          <p className="text-sm font-mono" style={{ color: 'var(--dl-text-dim)' }}>
            Analyze a repository from the sidebar or header to generate architecture universe diagrams and layered blueprints.
          </p>
        </GlassPanel>
      </div>
    );
  }

  return <ArchitecturePage data={data} />;
};

