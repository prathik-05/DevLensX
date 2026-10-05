import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface WikiPageTreeItem {
  id: string;
  title: string;
  type: string;
  parent?: string | null;
}

export interface WikiContextState {
  analysisId: string | null;
  pageTree: WikiPageTreeItem[];
  pagesSummary: Record<string, string>;
  activePageId: string | null;
  activePageContent: any | null;
  loading: boolean;
}

export interface WikiContextType extends WikiContextState {
  setAnalysisId: (id: string) => void;
  setActivePage: (pageId: string) => void;
  setWikiData: (tree: WikiPageTreeItem[], summary: Record<string, string>) => void;
  setActivePageContent: (content: any) => void;
}

const WikiContext = createContext<WikiContextType | null>(null);

const initialState: WikiContextState = {
  analysisId: null,
  pageTree: [],
  pagesSummary: {},
  activePageId: null,
  activePageContent: null,
  loading: false,
};

export function WikiProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WikiContextState>(initialState);

  const setAnalysisId = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      analysisId: id,
      pageTree: [],
      pagesSummary: {},
      activePageId: null,
      activePageContent: null,
      loading: true,
    }));
  }, []);

  const setActivePage = useCallback((pageId: string) => {
    setState(prev => ({ ...prev, activePageId: pageId }));
  }, []);

  const setWikiData = useCallback((tree: WikiPageTreeItem[], summary: Record<string, string>) => {
    setState(prev => ({ ...prev, pageTree: tree, pagesSummary: summary, loading: false }));
  }, []);

  const setActivePageContent = useCallback((content: any) => {
    setState(prev => ({ ...prev, activePageContent: content }));
  }, []);

  return (
    <WikiContext.Provider value={{ ...state, setAnalysisId, setActivePage, setWikiData, setActivePageContent }}>
      {children}
    </WikiContext.Provider>
  );
}

export function useWikiContext(): WikiContextType {
  const ctx = useContext(WikiContext);
  if (!ctx) throw new Error('useWikiContext must be used within WikiProvider');
  return ctx;
}
