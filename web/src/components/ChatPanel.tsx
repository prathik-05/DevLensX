import React, { useState, useRef } from 'react';
import { Send, Map, Search, FlaskConical } from 'lucide-react';
import { chatAsk, chatStream, chatInWorkspace, type ChatMode, type ChatContext, type ChatResponse } from '../apiClient';
import { EvidenceCitation } from './EvidenceCitation';

interface ChatPanelProps {
  analysisRunId: string | null;
  context?: ChatContext | null;
  onNavigateTab?: (tab: string, query?: string) => void;
}

type ResearchProgress = { label: string; done: boolean; active?: boolean };

const MODE_META: Record<ChatMode, { label: string; icon: any; hint: string }> = {
  FAST: { label: 'Fast', icon: Search, hint: 'Targeted retrieval' },
  CODEMAP: { label: 'Codemap', icon: Map, hint: 'Graph walk' },
  DEEP_RESEARCH: { label: 'Deep Research', icon: FlaskConical, hint: 'Multi-stage' },
};

export const ChatPanel: React.FC<ChatPanelProps> = ({ analysisRunId, context }) => {
  const [mode, setMode] = useState<ChatMode>('FAST');
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<Array<{ role: 'user' | 'assistant'; text: string; resp?: ChatResponse }>>([]);
  const [loading, setLoading] = useState(false);
  const [streamTokens, setStreamTokens] = useState('');
  const [researchProgress, setResearchProgress] = useState<ResearchProgress[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const doAsk = async (msg?: string) => {
    const message = (msg ?? input).trim();
    if (!message || !analysisRunId) return;
    setInput('');
    setHistory(h => [...h, { role: 'user', text: message }]);
    setLoading(true);
    setStreamTokens('');
    setResearchProgress([]);

    // Use workspace chat when context has workspace-specific identifiers
    const useWorkspaceChat = context && (context.symbol_id || context.diagram_id || context.section_id);

    try {
      if (mode === 'DEEP_RESEARCH') {
        // Streaming path - use regular chatStream for now
        const progress: ResearchProgress[] = [
          { label: 'Planning research', done: false, active: true },
          { label: 'Graph analysis', done: false },
          { label: 'Source inspection', done: false },
          { label: 'Claim verification', done: false },
          { label: 'Synthesis', done: false },
        ];
        setResearchProgress([...progress]);
        let acc = '';
        await chatStream(analysisRunId, message, mode, context || null, (event, data) => {
          if (event === 'research_planned') {
            progress[0].done = true; progress[0].active = false;
            progress[1].active = true;
            setResearchProgress([...progress]);
          } else if (event === 'retrieval_started') {
            const ch = data.channel;
            if (ch === 'kuzu' && !progress[1].done) { progress[1].done = true; progress[1].active = false; progress[2].active = true; }
            setResearchProgress([...progress]);
          } else if (event === 'claim_verification_started') {
            progress[2].done = true; progress[2].active = false; progress[3].active = true;
            setResearchProgress([...progress]);
          } else if (event === 'answer_token') {
            acc += data.token || '';
            setStreamTokens(acc);
          } else if (event === 'research_complete') {
            progress.forEach(p => { p.done = true; p.active = false; });
            setResearchProgress([...progress]);
            const resp = data as ChatResponse;
            setHistory(h => [...h, { role: 'assistant', text: resp.answer || acc, resp }]);
            setStreamTokens('');
          }
        });
        // Fallback if streaming didn't yield a final event (e.g. network close)
        if (acc && !history.some(h => h.text === acc)) {
          // handled via research_complete
        }
      } else if (useWorkspaceChat) {
        // Use workspace chat with full context
        const resp = await chatInWorkspace(analysisRunId, message, mode, context || null);
        setHistory(h => [...h, { role: 'assistant', text: resp.answer, resp }]);
      } else {
        const resp = await chatAsk(analysisRunId, message, mode, context || null);
        setHistory(h => [...h, { role: 'assistant', text: resp.answer, resp }]);
      }
    } catch (e: any) {
      setHistory(h => [...h, { role: 'assistant', text: `Error: ${e.message?.slice(0, 300)}` }]);
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollTo({ top: 99999, behavior: 'smooth' }), 50);
    }
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-slate-700 bg-[#0B0F19] overflow-hidden">
      {/* Mode switcher */}
      <div className="flex items-center gap-1 p-2 border-b border-slate-800 bg-[#111827]">
        {(Object.keys(MODE_META) as ChatMode[]).map(m => {
          const meta = MODE_META[m];
          const Icon = meta.icon;
          const active = mode === m;
          return (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono font-bold border transition-all ${active ? 'bg-indigo-600 text-white border-indigo-500 shadow' : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'}`}
              title={meta.hint}
            >
              <Icon className="w-3.5 h-3.5" /> {meta.label}
            </button>
          );
        })}
      </div>

      {/* History */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {history.length === 0 && (
          <div className="text-xs font-mono text-slate-500 p-3 text-center border border-dashed border-slate-700 rounded-xl">
            Ask about this repository. Citations resolve through the snapshot that produced this page.
          </div>
        )}
        {history.map((item, idx) => (
          <div key={idx} className={`p-2.5 rounded-xl text-xs ${item.role === 'user' ? 'bg-indigo-500/10 border border-indigo-500/30 ml-6' : 'bg-[#111827] border border-slate-700 mr-2'}`}>
            <div className="font-mono text-[10px] uppercase tracking-wide opacity-60 mb-1">{item.role}</div>
            <div className="whitespace-pre-wrap leading-relaxed font-sans text-slate-100">{item.text}</div>
            {item.resp && (
              <div className="mt-2 space-y-2">
                {/* Verdict summary */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  {item.resp.claims.slice(0, 4).map((c, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border bg-slate-900 border-slate-700">
                      <span className={c.verdict.includes('VERIFIED') ? 'text-emerald-400' : c.verdict.includes('SUGGESTION') ? 'text-sky-400' : 'text-rose-400'}>{c.verdict}</span>
                      <span className="text-slate-400">{c.subject} {c.predicate} {c.object}</span>
                    </span>
                  ))}
                </div>
                {/* Citations */}
                {item.resp.evidence_refs.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {item.resp.evidence_refs.slice(0, 3).map((r, i) => (
                      <EvidenceCitation key={i} ref={{ repository_id: r.repository_id, analysis_run_id: r.analysis_run_id, file_path: r.file_path, line_start: r.line_start, line_end: r.line_end, commit_hash: (r as any).commit_hash, symbol_name: r.symbol_name } as any} compact />
                    ))}
                  </div>
                )}
                {/* Diagram (Codemap / Deep Research) */}
                {item.resp.diagrams[0] && (
                  <div className="rounded-lg border border-slate-700 overflow-hidden bg-[#0B0F19] p-2">
                    <div className="text-[10px] font-mono text-slate-400 mb-1">{item.resp.diagrams[0].type}</div>
                    <div className="flex flex-wrap gap-1">
                      {(item.resp.diagrams[0].nodes || []).slice(0, 10).map((n: any) => (
                        <span key={n.id} className="px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-[10px] font-mono">{n.label || n.id}</span>
                      ))}
                    </div>
                    {(item.resp.diagrams[0].edges || []).length > 0 && (
                      <div className="mt-1 text-[10px] font-mono text-slate-500">{item.resp.diagrams[0].edges.length} edges</div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && mode === 'DEEP_RESEARCH' && (
          <div className="space-y-1 p-2 rounded-xl border border-slate-700 bg-[#111827]">
            <div className="text-[10px] font-mono font-bold uppercase tracking-wide text-slate-400">Deep Research</div>
            {researchProgress.map((p, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] font-mono">
                <span className={p.done ? 'text-emerald-400' : p.active ? 'text-sky-400 animate-pulse' : 'text-slate-500'}>{p.done ? '✓' : p.active ? '●' : '○'}</span>
                <span className={p.done ? 'text-slate-200' : p.active ? 'text-white' : 'text-slate-500'}>{p.label}</span>
              </div>
            ))}
            {streamTokens && <div className="text-xs font-sans text-slate-300 whitespace-pre-wrap mt-2 p-2 rounded bg-[#0B0F19] border border-slate-800">{streamTokens.slice(0, 800)}</div>}
          </div>
        )}
        {loading && mode !== 'DEEP_RESEARCH' && (
          <div className="text-xs font-mono text-slate-400 animate-pulse p-2">Thinking…</div>
        )}
      </div>

      {/* Input */}
      <div className="p-2 border-t border-slate-800 flex items-center gap-1.5 bg-[#111827]">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doAsk()}
          placeholder={context?.selected_symbol ? `Ask about ${context.selected_symbol}…` : 'Ask about this repository…'}
          className="flex-1 bg-[#0B0F19] border border-slate-700 rounded-lg px-2.5 py-2 text-xs font-mono text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
          disabled={loading || !analysisRunId}
        />
        <button onClick={() => doAsk()} disabled={loading || !analysisRunId || !input.trim()} className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white">
          <Send className="w-4 h-4" />
        </button>
      </div>
      {!analysisRunId && <div className="px-2 pb-2 text-[10px] font-mono text-amber-400">Analyze a repository first to enable chat.</div>}
    </div>
  );
};