import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { analyzeRepo, uploadZipRepo } from './apiClient';

interface AppState {
  // Repository & Analysis
  repoPath: string;
  setRepoPath: (path: string) => void;

  analysisId: string | null;
  setAnalysisId: (id: string | null) => void;

  // Real analysis result from POST /api/analyze (null until analyzed).
  // Never fabricated: on backend failure analysisError is set instead.
  analysisData: any | null;
  setAnalysisData: (data: any) => void;
  analysisError: string | null;

  isAnalyzing: boolean;
  setIsAnalyzing: (v: boolean) => void;

  /** Run full backend analysis for a repo path or GitHub URL. */
  runAnalysis: (path?: string) => Promise<any | null>;
  /** Upload a .zip archive and analyze it. */
  uploadAndAnalyze: (file: File) => Promise<any | null>;

  // Hallucination injection for testing
  injectHallucination: boolean;
  setInjectHallucination: (v: boolean) => void;

  // Code Turtle / AI Review
  codeReviewEnabled: boolean;
  setCodeReviewEnabled: (v: boolean) => void;

  codeReviewConfig: {
    provider: 'azure' | 'openai' | 'local' | 'anthropic';
    endpoint: string;
    deployment: string;
    apiKey: string;
    apiVersion: string;
    model: string;
  };
  setCodeReviewConfig: (config: Partial<AppState['codeReviewConfig']>) => void;

  // UI State
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;

  // Theme State (Light / Dark)
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // Notifications
  notifications: Array<{ id: string; type: 'info' | 'success' | 'warning' | 'error'; message: string; timestamp: number }>;
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
}

const defaultCodeReviewConfig = {
  provider: 'azure' as const,
  endpoint: '',
  deployment: '',
  apiKey: '',
  apiVersion: '2024-02-15-preview',
  model: 'gpt-4',
};

export const useAppStore = create<AppState>()(
  subscribeWithSelector((set, get) => ({
    repoPath: '',
    setRepoPath: (path) => set({ repoPath: path }),

    analysisId: null,
    setAnalysisId: (id) => set({ analysisId: id }),

    analysisData: null,
    setAnalysisData: (data) => set({
      analysisData: data,
      analysisId: data?.analysis_run_id ?? null,
    }),
    analysisError: null,

    isAnalyzing: false,
    setIsAnalyzing: (v) => set({ isAnalyzing: v }),

    runAnalysis: async (path?: string) => {
      const target = (path ?? get().repoPath).trim();
      if (!target || get().isAnalyzing) return null;
      set({ isAnalyzing: true, analysisError: null });
      try {
        const data = await analyzeRepo(target, get().injectHallucination);
        set({
          analysisData: data,
          analysisId: data?.analysis_run_id ?? null,
          repoPath: target,
          isAnalyzing: false,
        });
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Analysis failed';
        set({ analysisError: message, isAnalyzing: false });
        return null;
      }
    },

    uploadAndAnalyze: async (file: File) => {
      if (get().isAnalyzing) return null;
      set({ isAnalyzing: true, analysisError: null });
      try {
        const data = await uploadZipRepo(file);
        set({
          analysisData: data,
          analysisId: data?.analysis_run_id ?? null,
          repoPath: data?.repository ?? file.name,
          isAnalyzing: false,
        });
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        set({ analysisError: message, isAnalyzing: false });
        return null;
      }
    },

    injectHallucination: false,
    setInjectHallucination: (v) => set({ injectHallucination: v }),

    codeReviewEnabled: true,
    setCodeReviewEnabled: (v) => set({ codeReviewEnabled: v }),

    codeReviewConfig: defaultCodeReviewConfig,
    setCodeReviewConfig: (config) =>
      set((state) => ({
        codeReviewConfig: { ...state.codeReviewConfig, ...config },
      })),

    sidebarCollapsed: false,
    setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

    theme: typeof window !== 'undefined'
      ? (localStorage.getItem('devlensx_theme') as 'light' | 'dark' || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
      : 'light',
    setTheme: (theme) => {
      if (typeof window !== 'undefined') {
        localStorage.setItem('devlensx_theme', theme);
        const root = document.documentElement;
        root.classList.add('theme-transitioning');
        window.clearTimeout((window as any).__themeTransitionTimer);
        (window as any).__themeTransitionTimer = window.setTimeout(() => {
          root.classList.remove('theme-transitioning');
        }, 350);
        root.setAttribute('data-theme', theme);
        root.classList.toggle('dark', theme === 'dark');
        root.style.colorScheme = theme;
      }
      set({ theme });
    },
    toggleTheme: () => {
      const next = get().theme === 'light' ? 'dark' : 'light';
      get().setTheme(next);
    },

    notifications: [],
    addNotification: (notification) =>
      set((state) => ({
        notifications: [
          ...state.notifications,
          { ...notification, id: Math.random().toString(36).slice(2), timestamp: Date.now() },
        ],
      })),
    removeNotification: (id) =>
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      })),
  }))
);

// Helper to trigger analysis from anywhere
export function triggerAnalysis(path?: string) {
  const { runAnalysis } = useAppStore.getState();
  return runAnalysis(path);
}
