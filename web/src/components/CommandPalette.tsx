import React, { useState, useEffect } from 'react';
import type { AnalysisResponse } from '../types';
import { Search, FileCode, ShieldAlert, Bot, X, BookOpen, MapPinned } from 'lucide-react';
import { useWikiContext } from '../wikiContext';
import { GlassModal } from './GlassPanel';
import { Badge } from './Badge';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  data: AnalysisResponse;
  onSelectAction: (actionType: string, payload?: any) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  data,
  onSelectAction,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  let wikiPages: any[] = [];
  try {
    const wiki = useWikiContext();
    wikiPages = wiki.pageTree || [];
  } catch {
    wikiPages = [];
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const nodes = data.knowledge_graph?.nodes || [];
  const recs = data.top_engineering_recommendations || [];

  const filteredNodes = nodes.filter(n =>
    n.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    n.stereotype.toLowerCase().includes(searchTerm.toLowerCase())
  ).slice(0, 5);

  const filteredRecs = recs.filter(r =>
    r.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.reason.toLowerCase().includes(searchTerm.toLowerCase())
  ).slice(0, 3);

  const filteredWiki = wikiPages.filter(p =>
    p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.type && p.type.toLowerCase().includes(searchTerm.toLowerCase()))
  ).slice(0, 5);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 p-4"
      style={{ backgroundColor: 'rgba(9, 11, 14, 0.8)', backdropFilter: 'blur(8px)' }}>
      <GlassModal padding="none" className="max-w-xl w-full animate-in fade-in zoom-in-95 duration-150">
        {/* Search Input Header */}
        <div className="p-4 border-b flex items-center space-x-3" style={{ borderColor: 'var(--glass-modal-border)' }}>
          <Search className="w-5 h-5 shrink-0" style={{ color: 'var(--dl-primary)' }} />
          <input
            type="text"
            autoFocus
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search classes, files, wiki pages, recommendations, or ask Copilot (Ctrl + K)..."
            className="w-full bg-transparent text-sm text-white placeholder-[var(--dl-tertiary)] focus:outline-none font-mono"
          />
          <button onClick={onClose} className="text-[var(--dl-tertiary)] hover:text-white p-1 dl-transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="p-4 space-y-4 max-h-[350px] overflow-y-auto font-mono text-xs">
          {/* Quick Copilot Action */}
          {searchTerm && (
            <div className="space-y-1">
              <span className="dl-section-title block">Ask Engineering Copilot</span>
              <button
                onClick={() => { onSelectAction('copilot_prompt', searchTerm); onClose(); }}
                className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-[var(--dl-cyan)] dl-transition-colors"
              >
                <div className="flex items-center space-x-2 truncate">
                  <Bot className="w-4 h-4 shrink-0" style={{ color: 'var(--dl-cyan)' }} />
                  <span className="truncate font-medium text-white">Ask Copilot: &ldquo;{searchTerm}&rdquo;</span>
                </div>
                <kbd className="dl-kbd">Enter</kbd>
              </button>
            </div>
          )}

          {/* Wiki Pages */}
          {filteredWiki.length > 0 && (
            <div className="space-y-1">
              <span className="dl-section-title block">Wiki Pages ({filteredWiki.length})</span>
              {filteredWiki.map(p => (
                <button
                  key={p.id}
                  onClick={() => { onSelectAction('navigate_wiki', p.id); onClose(); }}
                  className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-white dl-transition-colors"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <BookOpen className="w-4 h-4 shrink-0" style={{ color: 'var(--dl-indigo)' }} />
                    <span className="font-bold truncate">{p.title}</span>
                    <Badge variant="finding-perf" size="sm">{p.type}</Badge>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Classes / Components */}
          {filteredNodes.length > 0 && (
            <div className="space-y-1">
              <span className="dl-section-title block">Source Components ({filteredNodes.length})</span>
              {filteredNodes.map(n => (
                <button
                  key={n.id}
                  onClick={() => { onSelectAction('navigate_explorer', n.file); onClose(); }}
                  className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-white dl-transition-colors"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <FileCode className="w-4 h-4 shrink-0" style={{ color: 'var(--dl-tertiary)' }} />
                    <span className="font-bold truncate">{n.name}</span>
                    <Badge variant="not-verified" size="sm">{n.stereotype}</Badge>
                  </div>
                  <span className="text-[10px] truncate max-w-[120px]" style={{ color: 'var(--dl-tertiary)' }}>{n.file}</span>
                </button>
              ))}
            </div>
          )}

          {/* Security Recommendations */}
          {filteredRecs.length > 0 && (
            <div className="space-y-1">
              <span className="dl-section-title block">Security & Risk Recommendations</span>
              {filteredRecs.map(r => (
                <button
                  key={r.rank}
                  onClick={() => { onSelectAction('navigate_security'); onClose(); }}
                  className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-white dl-transition-colors"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <ShieldAlert className="w-4 h-4 shrink-0" style={{ color: 'var(--semantic-risk-high)' }} />
                    <span className="font-bold truncate">{r.title}</span>
                  </div>
                  <Badge variant={`risk-${r.priority.toLowerCase()}` as 'risk-high' | 'risk-medium' | 'risk-low'} size="sm">
                    {r.priority}
                  </Badge>
                </button>
              ))}
            </div>
          )}

          {/* Wiki & Codemap quick navigation */}
          <div className="space-y-1 border-t pt-3" style={{ borderColor: 'var(--glass-modal-border)' }}>
            <span className="dl-section-title block">Wiki & Codemap</span>
            <button onClick={() => { onSelectAction('navigate_wiki'); onClose(); }} className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-white dl-transition-colors">
              <div className="flex items-center space-x-2"><BookOpen className="w-4 h-4" style={{ color: 'var(--dl-indigo)' }} /><span className="font-bold">Open Wiki Generator</span></div>
            </button>
            <button onClick={() => { onSelectAction('navigate_codemap'); onClose(); }} className="w-full text-left p-2.5 rounded-xl dl-btn-subtle flex items-center justify-between text-white dl-transition-colors">
              <div className="flex items-center space-x-2"><MapPinned className="w-4 h-4" style={{ color: 'var(--dl-green)' }} /><span className="font-bold">Open Codemap Tour</span></div>
            </button>
          </div>

          {!searchTerm && filteredWiki.length === 0 && (
            <div className="text-center py-6" style={{ color: 'var(--dl-tertiary)' }}>
              Type to search AST components, wiki pages, security findings, or ask Copilot directly.
            </div>
          )}
        </div>

        <div className="p-3 border-t bg-[var(--dl-bg-elevated)] text-center" style={{ borderColor: 'var(--glass-modal-border)' }}>
          <span className="text-[10px] font-mono" style={{ color: 'var(--dl-tertiary)' }}>
            Press <kbd className="dl-kbd ml-1">Esc</kbd> to exit search
          </span>
        </div>
      </GlassModal>
    </div>
  );
};