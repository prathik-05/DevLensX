import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface WorkspaceContextState {
  repository_id: string;
  analysis_run_id: string;
  commit_hash: string | null;
  active_page: string | null;
  active_section: string | null;
  active_symbol: string | null;
  active_diagram: string | null;
  selected_files: string[];
  selected_evidence: any[];
  current_task: string | null;
  mode: string | null;
  workspace_name?: string;
  repositories?: any[];
}

export interface WorkspaceContextType extends WorkspaceContextState {
  setContext: (updates: Partial<WorkspaceContextState>) => void;
  clearContext: () => void;
  updateFromAPI: (data: any) => void;
  switchRepository?: (repoId: string) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

const initialState: WorkspaceContextState = {
  repository_id: '',
  analysis_run_id: '',
  commit_hash: null,
  active_page: null,
  active_section: null,
  active_symbol: null,
  active_diagram: null,
  selected_files: [],
  selected_evidence: [],
  current_task: null,
  mode: null,
};

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [context, setContextState] = useState<WorkspaceContextState>(initialState);

  const setContext = useCallback((updates: Partial<WorkspaceContextState>) => {
    setContextState(prev => ({ ...prev, ...updates }));
  }, []);

  const clearContext = useCallback(() => {
    setContextState(initialState);
  }, []);

  const updateFromAPI = useCallback((data: any) => {
    if (!data) return;
    const updates: Partial<WorkspaceContextState> = {};
    if (data.repository_id) updates.repository_id = data.repository_id;
    if (data.analysis_run_id) updates.analysis_run_id = data.analysis_run_id;
    if (data.commit_hash) updates.commit_hash = data.commit_hash;
    if (data.context) {
      if (data.context.page_id) updates.active_page = data.context.page_id;
      if (data.context.section_id) updates.active_section = data.context.section_id;
      if (data.context.symbol_id) updates.active_symbol = data.context.symbol_id;
      if (data.context.diagram_id) updates.active_diagram = data.context.diagram_id;
    }
    setContextState(prev => ({ ...prev, ...updates }));
  }, []);

  return (
    <WorkspaceContext.Provider value={{ ...context, setContext, clearContext, updateFromAPI }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspaceContext(): WorkspaceContextType {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspaceContext must be used within a WorkspaceProvider');
  }
  return context;
}

export function useWorkspaceSnapshot() {
  const { repository_id, analysis_run_id, commit_hash } = useWorkspaceContext();
  return { repository_id, analysis_run_id, commit_hash };
}