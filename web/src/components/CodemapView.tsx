import React, { useEffect, useState } from 'react';
import { fetchCodemap } from '../apiClient';
import { Map, ExternalLink, FileCode, ChevronLeft, ChevronRight } from 'lucide-react';
import { useWorkspaceContext } from '../workspaceContext';
import { GlassPanel } from './GlassPanel';
import { Badge } from './Badge';
import { CodemapStopSkeleton } from './Skeleton';

export const CodemapView: React.FC = () => {
  const { analysis_run_id, setContext } = useWorkspaceContext();
  const analysisId = analysis_run_id;
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentIdx, setCurrentIdx] = useState(0);

  useEffect(() => {
    if (!analysisId) return;
    let cancelled = false;
    const controller = new AbortController();
    setError(null);
    setData(null);
    setCurrentIdx(0);
    fetchCodemap(analysisId, controller.signal)
      .then(res => {
        if (cancelled || controller.signal.aborted) return;
        setData(res);
        if (res?.stops?.length) setCurrentIdx(0);
      })
      .catch(err => {
        if (cancelled) return;
        if ((err as any)?.name === 'AbortError') return;
        setError((err as Error).message || 'Failed to load codemap');
      });
    return () => { cancelled = true; controller.abort(); };
  }, [analysisId]);

  useEffect(() => {
    const stops: any[] = data?.stops || [];
    if (stops[currentIdx]?.class_name) {
      setContext({ active_symbol: stops[currentIdx].class_name });
    }
  }, [currentIdx, data, setContext]);

  const gotoStop = (idx: number, className?: string) => {
    setCurrentIdx(idx);
    if (className) setContext({ active_symbol: className });
  };

  if (!analysisId) {
    return (
      <div className="dl-flex-center" style={{ minHeight: '50vh' }}>
        <GlassPanel className="p-6 text-center" style={{ maxWidth: '420px' }}>
          <Map className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--dl-accent)' }} />
          <h2 className="text-base font-bold text-black dark:text-white mb-1">No analysis selected</h2>
          <p className="text-sm" style={{ color: 'var(--dl-text-dim)' }}>Run an analysis from the sidebar to generate the code map.</p>
        </GlassPanel>
      </div>
    );
  }
  if (error) {
    return (
      <GlassPanel className="p-4 dl-flex-gap-2" style={{ borderColor: 'var(--semantic-insufficient-border)' }}>
        <span className="text-xs font-mono" style={{ color: 'var(--semantic-insufficient)' }}>ERROR: {error}</span>
      </GlassPanel>
    );
  }
  if (!data) {
    return (
      <div className="space-y-3">
        <div className="dl-flex-gap-3">
          <Map className="w-5 h-5" style={{ color: 'var(--dl-accent)' }} />
          <span className="dl-panel-label">CODE MAP</span>
          <span className="dl-caret text-xs font-mono" style={{ color: 'var(--dl-accent)' }}>generating</span>
        </div>
        {[0, 1, 2].map(i => <CodemapStopSkeleton key={i} />)}
      </div>
    );
  }

  const stops: any[] = data.stops || [];
  const activeStop = stops[currentIdx] ?? null;
  const highlightedNodeId = activeStop?.class_name ?? null;

  return (
    <div className="space-y-4 dl-fade-in">
      {/* Header */}
      <GlassPanel className="p-4 dl-flex-between flex-wrap gap-3">
        <div className="dl-flex-gap-3">
          <div className="w-10 h-10 rounded-sm flex items-center justify-center" style={{ background: 'var(--dl-accent-soft)', border: '1px solid var(--dl-accent)' }}>
            <Map className="w-5 h-5" style={{ color: 'var(--dl-accent)' }} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-black dark:text-white">Code Map Tour</h1>
            <p className="text-[11px] font-mono" style={{ color: 'var(--dl-text-dim)' }}>
              {data.count ?? stops.length} stops · blast-radius order · <span className="dl-truncate">{analysisId}</span>
            </p>
          </div>
        </div>
        {stops.length > 0 && (
          <div className="dl-flex-gap-2 ml-auto">
            <button onClick={() => gotoStop(Math.max(0, currentIdx - 1))} disabled={currentIdx === 0} aria-label="Previous tour stop" className="dl-btn-ghost dl-btn-icon p-1.5">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono" style={{ color: 'var(--dl-text)' }} aria-live="polite">
              {String(currentIdx + 1).padStart(2, '0')}/{String(stops.length).padStart(2, '0')}
            </span>
            <button onClick={() => gotoStop(Math.min(stops.length - 1, currentIdx + 1))} disabled={currentIdx >= stops.length - 1} aria-label="Next tour stop" className="dl-btn-ghost dl-btn-icon p-1.5">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </GlassPanel>

      {/* Active stop */}
      {stops.length > 0 && activeStop && (
        <GlassPanel className="p-4 space-y-2" style={{ borderColor: 'var(--dl-accent)' }}>
          <div className="dl-flex-between">
            <span className="dl-panel-label">NOW TOURING</span>
            <span className="text-[11px] font-mono" style={{ color: 'var(--dl-text-dim)' }}>{activeStop.file}#L{activeStop.line_start}</span>
          </div>
          <div className="text-base font-bold font-mono text-black dark:text-white">{activeStop.class_name}</div>
          <p className="text-sm" style={{ color: 'var(--dl-text-dim)' }}>{activeStop.annotation}</p>
          <div className="h-1 rounded-sm overflow-hidden" style={{ background: 'var(--dl-bg-elevated)' }} role="progressbar" aria-valuenow={currentIdx + 1} aria-valuemin={1} aria-valuemax={stops.length} aria-label="Tour progress">
            <div className="h-full rounded-sm transition-all duration-140" style={{ width: `${((currentIdx + 1) / stops.length) * 100}%`, background: 'var(--dl-accent)' }} />
          </div>
        </GlassPanel>
      )}

      {/* Stops list */}
      <GlassPanel className="p-4 space-y-2">
        <div className="dl-flex-between mb-1">
          <span className="dl-panel-label">TOUR STOPS — BLAST-RADIUS RANKED</span>
          <Badge variant="finding-perf" size="sm">{stops.length} STOPS</Badge>
        </div>
        {stops.map((s: any) => {
          const isActive = s.class_name === highlightedNodeId;
          const key = s.id ?? `${s.file}-${s.class_name}-${s.order}`;
          return (
            <div
              key={key}
              onClick={() => gotoStop(stops.findIndex(x => (x.id ?? x.class_name) === (s.id ?? s.class_name)), s.class_name)}
              role="button"
              tabIndex={0}
              aria-label={`Tour stop ${s.order}: ${s.class_name}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  gotoStop(stops.findIndex(x => (x.id ?? x.class_name) === (s.id ?? s.class_name)), s.class_name);
                }
              }}
              className="p-3 rounded-sm dl-flex-between gap-3 cursor-pointer transition-all duration-100"
              style={{
                background: isActive ? 'var(--dl-accent-soft)' : 'var(--dl-surface)',
                border: `1px solid ${isActive ? 'var(--dl-accent)' : 'var(--dl-panel-border)'}`,
              }}
            >
              <div className="space-y-1 flex-1 min-w-0">
                <div className="dl-flex-gap-2 font-mono text-xs flex-wrap">
                  <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-bold" style={{ background: 'var(--dl-bg-elevated)', color: 'var(--dl-accent)', border: '1px solid var(--dl-accent)' }}>#{s.order}</span>
                  <span className="text-black dark:text-white font-bold">{s.class_name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-sm" style={{ background: 'var(--dl-bg-elevated)', color: 'var(--dl-text-dim)', border: '1px solid var(--dl-panel-border)' }}>{s.stereotype}</span>
                  <span className="text-[10px] font-mono" style={{ color: 'var(--semantic-verified)' }}>blast {s.blast_radius}</span>
                </div>
                <p className="text-xs" style={{ color: 'var(--dl-text-dim)' }}>{s.annotation}</p>
                <p className="dl-flex-gap-2 text-[11px] font-mono" style={{ color: 'var(--dl-text-muted)' }}>
                  <FileCode className="w-3.5 h-3.5" />
                  <span className="truncate">{s.file}</span>
                  <span>#L{s.line_start}</span>
                </p>
              </div>
              <span className="text-[10px] font-mono flex-shrink-0 hidden sm:inline" style={{ color: 'var(--dl-text-muted)' }}>
                <ExternalLink className="w-3.5 h-3.5 inline" /> jump
              </span>
            </div>
          );
        })}
        {stops.length === 0 && (
          <div className="text-center py-8 text-xs font-mono" style={{ color: 'var(--dl-text-muted)' }}>
            No tour stops — run analysis to generate the blast-radius tour<span className="dl-caret" />
          </div>
        )}
      </GlassPanel>
    </div>
  );
};
