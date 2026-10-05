import React, { useEffect, useState } from 'react';
import {
  Compass,
  FileCode,
  Layers,
  Code2,
  Database,
  Cpu,
  Monitor,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';
import { useAppStore } from '../store';
import { fetchGuidedTour } from '../apiClient';
import type { GuidedTourResult, GuidedTourStep } from '../apiClient';

const tourPresets = [
  { id: 'user-request-flow', title: 'Complete Request Lifecycle', desc: 'From UI interaction to API, Business Logic, AI Engine & Database' },
  { id: 'auth-security-flow', title: 'Authentication & Guard Flow', desc: 'JWT interceptors, security filter chain, and principal verification' },
  { id: 'persistence-query-flow', title: 'Database Persistence Flow', desc: 'JPA entity mapping, transaction management & repository execution' }
];

export const GuidedToursView: React.FC = () => {
  const { repoPath, analysisData } = useAppStore();
  const repoName = analysisData?.repository || repoPath || 'Repository';

  const [selectedTourId, setSelectedTourId] = useState<string>('user-request-flow');
  const [tourData, setTourData] = useState<GuidedTourResult | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchGuidedTour(selectedTourId)
      .then(res => {
        if (mounted) {
          setTourData(res);
          setActiveStepIndex(0);
          setLoading(false);
        }
      })
      .catch(err => {
        console.error(err);
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [selectedTourId]);

  const activeStep: GuidedTourStep | undefined = tourData?.steps[activeStepIndex];

  const getLayerIcon = (layer: string) => {
    const l = layer.toLowerCase();
    const iconClass = "w-4 h-4 text-black dark:text-zinc-200";
    if (l.includes('user') || l.includes('client')) return <Monitor className={iconClass} />;
    if (l.includes('ui') || l.includes('component')) return <Layers className={iconClass} />;
    if (l.includes('api') || l.includes('router') || l.includes('controller')) return <Code2 className={iconClass} />;
    if (l.includes('service') || l.includes('business')) return <Cpu className={iconClass} />;
    if (l.includes('ai') || l.includes('intelligence')) return <ShieldCheck className={iconClass} />;
    if (l.includes('database') || l.includes('persistence')) return <Database className={iconClass} />;
    return <FileCode className={iconClass} />;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 font-mono">
      {/* Header */}
      <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 border border-black dark:border-zinc-700 bg-black dark:bg-zinc-800 text-white dark:text-zinc-200 rounded-sm">
                CODE-CENTRIC TOURS
              </span>
              <span className="text-xs font-bold text-neutral-500 dark:text-zinc-400 uppercase tracking-wider">
                {repoName}
              </span>
            </div>
            <h1 className="text-2xl font-black uppercase tracking-tight text-black dark:text-zinc-100 flex items-center gap-2">
              <Compass className="w-6 h-6 text-zinc-800 dark:text-zinc-200" />
              <span>Guided Request Execution Tours</span>
            </h1>
            <p className="text-xs text-neutral-600 dark:text-zinc-400 mt-1 font-sans">
              Step-by-step interactive walkthroughs tracing real application requests across architecture tiers: User → UI → API → Service → AI → DB → Response.
            </p>
          </div>

          {/* Tour selector tabs */}
          <div className="flex flex-wrap gap-1 p-1 border border-black/20 dark:border-zinc-800 bg-neutral-100 dark:bg-[#18191f] rounded-sm">
            {tourPresets.map(preset => (
              <button
                key={preset.id}
                onClick={() => setSelectedTourId(preset.id)}
                className={`px-3 py-1.5 text-xs font-bold uppercase transition-all rounded-sm ${
                  selectedTourId === preset.id
                    ? 'bg-black text-white dark:bg-zinc-800 dark:text-zinc-100 shadow-sm border border-black dark:border-zinc-700'
                    : 'bg-white text-black dark:bg-[#121316] dark:text-zinc-400 hover:bg-neutral-200 dark:hover:bg-zinc-800/60'
                }`}
              >
                {preset.title.split(' ')[0]} Flow
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-12 text-center shadow-sm dark:shadow-none rounded-sm">
          <div className="animate-pulse text-xs font-bold uppercase tracking-wider text-neutral-600 dark:text-zinc-400">
            Synthesizing Guided Tour Execution Steps...
          </div>
        </div>
      ) : tourData ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Step Sequence List */}
          <div className="lg:col-span-1 border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-4 shadow-sm dark:shadow-none rounded-sm space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-black dark:text-zinc-100 mb-3 pb-2 border-b border-neutral-200 dark:border-zinc-800 flex items-center justify-between">
              <span>Execution Steps</span>
              <span className="text-[10px] text-neutral-500 dark:text-zinc-400 font-mono">
                {tourData.steps.length} Steps
              </span>
            </h3>

            <div className="space-y-2">
              {tourData.steps.map((step, idx) => {
                const isActive = idx === activeStepIndex;
                return (
                  <button
                    key={step.step}
                    onClick={() => setActiveStepIndex(idx)}
                    className={`w-full text-left p-2.5 border transition-all flex items-start gap-2.5 rounded-sm ${
                      isActive
                        ? 'border-black dark:border-zinc-600 bg-black text-white dark:bg-zinc-800 dark:text-zinc-100 shadow-sm'
                        : 'border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] text-black dark:text-zinc-300 hover:bg-neutral-50 dark:hover:bg-[#1f2029]'
                    }`}
                  >
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 border rounded-sm ${
                        isActive
                          ? 'border-white bg-white text-black dark:border-zinc-300 dark:bg-zinc-200 dark:text-zinc-900'
                          : 'border-black/20 dark:border-zinc-700 bg-neutral-100 dark:bg-[#121316] text-black dark:text-zinc-300'
                      }`}
                    >
                      {step.step}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 text-xs font-bold truncate">
                        <span>{step.layer}</span>
                      </div>
                      <div
                        className={`text-[10px] font-mono truncate mt-0.5 ${
                          isActive ? 'text-neutral-300 dark:text-zinc-400' : 'text-neutral-500 dark:text-zinc-500'
                        }`}
                      >
                        {step.symbol}
                      </div>
                    </div>
                    {isActive && <ChevronRight className="w-4 h-4 text-white dark:text-zinc-100 self-center" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Step Deep-Dive */}
          <div className="lg:col-span-2 space-y-6">
            {activeStep && (
              <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-4 border-b border-black/20 dark:border-zinc-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2 border border-black/20 dark:border-zinc-700 bg-neutral-100 dark:bg-[#18191f] rounded-sm">
                      {getLayerIcon(activeStep.layer)}
                    </div>
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400">
                        Step {activeStep.step} of {tourData.steps.length} — {activeStep.layer}
                      </div>
                      <h2 className="text-lg font-black uppercase tracking-tight text-black dark:text-zinc-100">
                        {activeStep.symbol}
                      </h2>
                    </div>
                  </div>

                  <span className="text-xs font-mono font-bold px-2 py-1 border border-black/20 dark:border-zinc-700 bg-neutral-100 dark:bg-[#18191f] text-black dark:text-zinc-200 rounded-sm">
                    {tourData.verdict}
                  </span>
                </div>

                <div className="font-sans text-xs space-y-3">
                  <div>
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 block mb-1">
                      Target File
                    </span>
                    <div className="p-2 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] font-mono text-xs text-black dark:text-zinc-200 font-bold flex items-center justify-between rounded-sm">
                      <span>{activeStep.file}</span>
                      <span className="text-[10px] uppercase text-neutral-500 dark:text-zinc-500 font-sans">Verified Path</span>
                    </div>
                  </div>

                  <div>
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 block mb-1">
                      Execution Behavior
                    </span>
                    <p className="text-neutral-800 dark:text-zinc-300 leading-relaxed bg-white dark:bg-[#16171d] p-3 border border-black/20 dark:border-zinc-800 rounded-sm">
                      {activeStep.description}
                    </p>
                  </div>

                  <div>
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 block mb-1">
                      Code Snippet / Implementation Hook
                    </span>
                    <pre className="p-3 border border-black/20 dark:border-zinc-800 bg-black dark:bg-[#0a0b0e] text-zinc-100 font-mono text-xs overflow-x-auto leading-relaxed rounded-sm">
                      {activeStep.snippet}
                    </pre>
                  </div>
                </div>

                {/* Step controls */}
                <div className="flex items-center justify-between pt-4 border-t border-black/20 dark:border-zinc-800">
                  <button
                    disabled={activeStepIndex === 0}
                    onClick={() => setActiveStepIndex(prev => Math.max(0, prev - 1))}
                    className="px-4 py-2 border border-black/20 dark:border-zinc-700 bg-white dark:bg-[#16171d] text-black dark:text-zinc-300 text-xs font-bold uppercase hover:bg-neutral-100 dark:hover:bg-[#20222a] disabled:opacity-30 shadow-sm dark:shadow-none transition-all rounded-sm"
                  >
                    Previous Step
                  </button>

                  <div className="text-xs font-mono font-bold text-neutral-700 dark:text-zinc-300">
                    {activeStepIndex + 1} / {tourData.steps.length}
                  </div>

                  <button
                    disabled={activeStepIndex === tourData.steps.length - 1}
                    onClick={() => setActiveStepIndex(prev => Math.min(tourData.steps.length - 1, prev + 1))}
                    className="px-4 py-2 border border-black dark:border-zinc-600 bg-black dark:bg-zinc-200 text-white dark:text-zinc-950 text-xs font-bold uppercase hover:bg-neutral-800 dark:hover:bg-white disabled:opacity-30 shadow-sm dark:shadow-none transition-all rounded-sm"
                  >
                    Next Step
                  </button>
                </div>
              </div>
            )}

            {/* Sequence Diagram Preview */}
            <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
              <h4 className="text-xs font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono mb-2">
                Mermaid Sequence Specification
              </h4>
              <p className="text-xs font-sans text-neutral-600 dark:text-zinc-400 mb-3">
                Deterministic execution flow derived from parsed controller endpoints, service bindings, and repository interfaces.
              </p>
              <pre className="p-3 border border-black/20 dark:border-zinc-800 bg-neutral-100 dark:bg-[#0c0d10] text-black dark:text-zinc-300 font-mono text-[11px] overflow-x-auto leading-relaxed rounded-sm">
                {tourData.mermaid_diagram}
              </pre>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
