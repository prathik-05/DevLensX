import React, { useState } from 'react';
import {
  Search,
  AlertTriangle,
  Send,
  CornerDownRight,
  ShieldCheck,
  Layers,
  HelpCircle,
  Cpu
} from 'lucide-react';
import { useAppStore } from '../store';
import {
  askCopilot,
  askWhereToEdit,
  askExplainConcept,
  getChangeImpact
} from '../apiClient';
import type {
  WhereToEditResult,
  ConceptExplanationResult
} from '../apiClient';

type AssistantTab = 'ask' | 'where-to-edit' | 'explain' | 'blast-radius';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  verdict?: string;
  timestamp: string;
}

const sampleQuestions = [
  'What is this repository about?',
  "Explain this project like I'm a beginner.",
  'What does Gemini/GPT do in this project?',
  'How does authentication work?',
  'Where is the database connected?',
  'What happens when a user uploads a file?',
  'Which files implement the RAG pipeline?'
];

const whereToEditPresets = [
  'Change the login button styling and click handler',
  'Add email notification on owner registration',
  'Add rate limiting to REST API endpoints',
  'Store user profile avatar in S3 or local disk',
  'Validate phone number format in Pet form'
];

const conceptPresets = ['Gemini', 'GPT', 'RAG', 'FAISS', 'Postgres', 'Spring', 'Redis', 'Docker'];

const renderAssistantMessage = (content: string) => {
  const lines = (content || '').split('\n');
  const elements: React.ReactNode[] = [];
  let inCode = false;
  let codeBuffer: string[] = [];

  const formatInline = (text: string) => {
    const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]*\))/g);
    return parts.map((part, idx) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        let codeText = part.slice(1, -1);
        codeText = codeText.replace(/\s*(?:thr|throw|thro)$/i, '').trim();
        return <code key={idx} className="px-1.5 py-0.5 bg-neutral-100 dark:bg-zinc-800 rounded font-mono text-[11px] text-zinc-800 dark:text-zinc-200">{codeText}</code>;
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={idx} className="font-semibold text-neutral-900 dark:text-white">{part.slice(2, -2)}</strong>;
      }
      const linkMatch = part.match(/^\[(.*?)\]\((.*?)\)$/);
      if (linkMatch) {
        const label = linkMatch[1];
        return (
          <span key={idx} className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 rounded font-mono text-[10px] bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border border-sky-300 dark:border-sky-800">
            📍 {label}
          </span>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim().startsWith('```')) {
      if (inCode) {
        elements.push(
          <pre key={`code-${i}`} className="p-2.5 my-2 bg-neutral-900 text-neutral-100 rounded text-[11px] font-mono overflow-x-auto">
            {codeBuffer.join('\n')}
          </pre>
        );
        codeBuffer = [];
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuffer.push(line);
      continue;
    }
    if (line.startsWith('### ')) {
      elements.push(<h4 key={`h4-${i}`} className="font-bold text-xs mt-3 mb-1 text-neutral-900 dark:text-zinc-100">{formatInline(line.slice(4))}</h4>);
    } else if (line.startsWith('## ')) {
      elements.push(<h3 key={`h3-${i}`} className="font-bold text-sm mt-3 mb-1 text-neutral-900 dark:text-zinc-100">{formatInline(line.slice(3))}</h3>);
    } else if (line.startsWith('# ')) {
      elements.push(<h2 key={`h2-${i}`} className="font-bold text-sm mt-4 mb-1.5 text-neutral-900 dark:text-zinc-100">{formatInline(line.slice(2))}</h2>);
    } else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      elements.push(
        <div key={`li-${i}`} className="flex items-start gap-1.5 my-0.5 pl-2 text-neutral-700 dark:text-zinc-300">
          <span className="text-neutral-400 dark:text-zinc-500">•</span>
          <span>{formatInline(line.trim().slice(2))}</span>
        </div>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={`sp-${i}`} className="h-1.5" />);
    } else {
      elements.push(<p key={`p-${i}`} className="my-1 text-neutral-800 dark:text-zinc-200">{formatInline(line)}</p>);
    }
  }

  if (inCode && codeBuffer.length > 0) {
    elements.push(
      <pre key="code-end" className="p-2.5 my-2 bg-neutral-900 text-neutral-100 rounded text-[11px] font-mono overflow-x-auto">
        {codeBuffer.join('\n')}
      </pre>
    );
  }

  return elements;
};

export const AIAssistantView: React.FC = () => {
  const { repoPath, analysisData, analysisId } = useAppStore();
  const repoName = analysisData?.repository || repoPath || 'Repository';

  const [activeTab, setActiveTab] = useState<AssistantTab>('ask');

  // 1. Ask Repository State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 Welcome! I'm your AI repository intelligence assistant for **${repoName}**.\n\nI can help you understand this codebase in depth. Here's what you can ask me:\n\n1. **Architecture & Structure** — How is the project organized? What are the main layers?\n2. **Technology & Frameworks** — What libraries are used and how?\n3. **Execution Flows** — What happens when a user does X? Trace a request end-to-end.\n4. **Code Locations** — Where is feature Y implemented? Which file handles Z?\n\nAll answers are grounded in actual parsed repository files — no hallucination.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isAsking, setIsAsking] = useState(false);

  // 2. Where Should I Edit State
  const [editQuery, setEditQuery] = useState('');
  const [editResult, setEditResult] = useState<WhereToEditResult | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  // 3. Concept State
  const [conceptQuery, setConceptQuery] = useState('');
  const [conceptResult, setConceptResult] = useState<ConceptExplanationResult | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);

  // 4. Blast Radius State
  const [targetClass, setTargetClass] = useState('OwnerController');
  const [blastResult, setBlastResult] = useState<any>(null);
  const [isCalculatingBlast, setIsCalculatingBlast] = useState(false);

  // Handle Ask Send
  const handleAskSubmit = async (queryText?: string) => {
    const q = (queryText || inputValue).trim();
    if (!q || isAsking) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!queryText) setInputValue('');
    setIsAsking(true);

    try {
      const history = messages.map(m => ({ q: m.role === 'user' ? m.content : '', a: m.role === 'assistant' ? m.content : '' }));
      const res = await askCopilot(q, history, repoName, analysisId || undefined);

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.plain_english || 'No response returned.',
        citations: (res as any).citations || [],
        verdict: (res as any).verdict || 'VERIFIED_EVIDENCE',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to answer question.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  // Handle Where Should I Edit
  const handleLocateEdit = async (queryToRun?: string) => {
    const q = (queryToRun || editQuery).trim();
    if (!q || isLocating) return;
    setIsLocating(true);
    try {
      const runId = analysisId || analysisData?.analysis_run_id;
      const res = await askWhereToEdit(q, runId);
      setEditResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLocating(false);
    }
  };

  // Handle Explain Concept
  const handleExplain = async (conceptToRun?: string) => {
    const c = (conceptToRun || conceptQuery).trim();
    if (!c || isExplaining) return;
    setIsExplaining(true);
    try {
      const runId = analysisId || analysisData?.analysis_run_id;
      const res = await askExplainConcept(c, runId);
      setConceptResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsExplaining(false);
    }
  };

  // Handle Blast Radius
  const handleCalculateBlast = async () => {
    if (!targetClass.trim() || isCalculatingBlast) return;
    setIsCalculatingBlast(true);
    try {
      const res = await getChangeImpact(analysisData?.analysis_run_id || 'latest', targetClass.trim());
      setBlastResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsCalculatingBlast(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 font-mono">
      {/* Header */}
      <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 border border-black dark:border-zinc-700 bg-black dark:bg-zinc-800 text-white dark:text-zinc-200 rounded-sm">
                INTELLIGENCE HUB
              </span>
              <span className="text-xs font-bold text-neutral-500 dark:text-zinc-400 uppercase tracking-wider">
                {repoName}
              </span>
            </div>
            <h1 className="text-2xl font-black uppercase tracking-tight text-black dark:text-zinc-100">
              AI Repository Intelligence & Copilot
            </h1>
            <p className="text-xs text-neutral-600 dark:text-zinc-400 mt-1 font-sans">
              Combines ChatGPT/Claude for codebase deep-dive with precise "Where Should I Edit" pinpointing and verified citations.
            </p>
          </div>

          {/* Tab Selection */}
          <div className="flex flex-wrap gap-1.5 p-1.5 border border-black/20 dark:border-zinc-800 bg-neutral-100 dark:bg-[#18191f] rounded">
            <button
              onClick={() => setActiveTab('ask')}
              className={`px-3.5 py-1.5 text-xs font-bold uppercase transition-all rounded ${
                activeTab === 'ask'
                  ? 'bg-blue-600 text-white shadow-sm border border-blue-500'
                  : 'bg-transparent text-neutral-600 dark:text-zinc-400 hover:bg-neutral-200 dark:hover:bg-zinc-800'
              }`}
            >
              Ask Repository
            </button>
            <button
              onClick={() => setActiveTab('where-to-edit')}
              className={`px-3.5 py-1.5 text-xs font-bold uppercase transition-all rounded ${
                activeTab === 'where-to-edit'
                  ? 'bg-blue-600 text-white shadow-sm border border-blue-500'
                  : 'bg-transparent text-neutral-600 dark:text-zinc-400 hover:bg-neutral-200 dark:hover:bg-zinc-800'
              }`}
            >
              Where Should I Edit?
            </button>
            <button
              onClick={() => setActiveTab('explain')}
              className={`px-3.5 py-1.5 text-xs font-bold uppercase transition-all rounded ${
                activeTab === 'explain'
                  ? 'bg-blue-600 text-white shadow-sm border border-blue-500'
                  : 'bg-transparent text-neutral-600 dark:text-zinc-400 hover:bg-neutral-200 dark:hover:bg-zinc-800'
              }`}
            >
              Explain Concepts
            </button>
            <button
              onClick={() => setActiveTab('blast-radius')}
              className={`px-3.5 py-1.5 text-xs font-bold uppercase transition-all rounded ${
                activeTab === 'blast-radius'
                  ? 'bg-blue-600 text-white shadow-sm border border-blue-500'
                  : 'bg-transparent text-neutral-600 dark:text-zinc-400 hover:bg-neutral-200 dark:hover:bg-zinc-800'
              }`}
            >
              Change Impact
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: ASK REPOSITORY */}
      {activeTab === 'ask' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Chat Stream */}
          <div className="lg:col-span-3 border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] flex flex-col h-[calc(100vh-220px)] min-h-[520px] shadow-sm dark:shadow-none rounded-sm">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map(msg => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400">
                      {msg.role === 'user' ? 'You' : 'DevLensX Assistant'}
                    </span>
                    <span className="text-[9px] text-neutral-400 dark:text-zinc-500">{msg.timestamp}</span>
                    {msg.verdict && (
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 border rounded-sm ${
                        msg.verdict.includes('VERIFIED')
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-700'
                          : msg.verdict.includes('SUGGESTION')
                          ? 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-700'
                          : 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-700'
                      }`}>
                        {msg.verdict.includes('VERIFIED') ? '✓ ' : msg.verdict.includes('SUGGESTION') ? '~ ' : '✗ '}
                        {msg.verdict}
                      </span>
                    )}
                  </div>

                  <div
                    className={`max-w-[85%] p-3.5 border text-xs leading-relaxed rounded-sm ${
                      msg.role === 'user'
                        ? 'border-black dark:border-zinc-700 bg-neutral-100 dark:bg-[#181920] text-black dark:text-zinc-200 shadow-sm'
                        : 'border-black/20 dark:border-[#26272e] bg-white dark:bg-[#16171d] text-black dark:text-zinc-200 shadow-sm dark:shadow-none'
                    }`}
                  >
                    <div className="font-sans text-xs leading-relaxed">
                      {msg.role === 'user' ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        renderAssistantMessage(msg.content)
                      )}
                    </div>

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-neutral-200 dark:border-zinc-800">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mb-1">
                          Verified Code Citations:
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {msg.citations.map((cite, i) => (
                            <span
                              key={i}
                              className="text-[10px] font-mono px-1.5 py-0.5 border border-sky-300 dark:border-sky-800 bg-sky-50 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 hover:bg-sky-100 dark:hover:bg-sky-900/60 transition-colors rounded-sm"
                            >
                              📍 {cite}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isAsking && (
                <div className="flex items-center gap-2.5 p-3 border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/30 text-indigo-900 dark:text-indigo-200 text-xs w-fit rounded-sm shadow-sm">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                  </div>
                  <span className="font-sans font-medium">Analyzing repository AST & Kùzu knowledge graph...</span>
                </div>
              )}
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] rounded-b-sm">
              <form
                onSubmit={e => {
                  e.preventDefault();
                  handleAskSubmit();
                }}
                className="flex gap-2"
              >
                <input
                  type="text"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  placeholder="Ask any question about this repository's code, structure, or workflows..."
                  disabled={isAsking}
                  className="flex-1 px-3 py-2 text-xs border border-black/30 dark:border-zinc-700 bg-white dark:bg-[#0e0f12] text-black dark:text-zinc-100 placeholder:text-neutral-400 dark:placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-500 shadow-sm dark:shadow-none rounded-sm"
                />
                <button
                  type="submit"
                  disabled={isAsking || !inputValue.trim()}
                  className="px-5 py-2 border border-indigo-700 dark:border-indigo-500 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold uppercase disabled:opacity-40 shadow-sm dark:shadow-none transition-all flex items-center gap-1.5 rounded-sm"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Ask</span>
                </button>
              </form>
            </div>
          </div>

          {/* Quick Prompts Sidebar */}
          <div className="space-y-4">
            <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-4 shadow-sm dark:shadow-none rounded-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-black dark:text-zinc-100 mb-2 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Suggested Questions</span>
              </h3>
              <p className="text-[11px] font-sans text-neutral-600 dark:text-zinc-400 mb-3">
                Click any prompt to instantly query the repository model:
              </p>
              <div className="space-y-1.5">
                {sampleQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputValue(q);
                      handleAskSubmit(q);
                    }}
                    className="w-full text-left p-2 text-xs font-sans border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] hover:bg-neutral-100 dark:hover:bg-[#20222a] text-black dark:text-zinc-300 transition-all shadow-sm dark:shadow-none rounded-sm"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>

            <div className="border border-black/20 dark:border-zinc-800 bg-neutral-100 dark:bg-[#16171d] p-4 shadow-sm dark:shadow-none rounded-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-black dark:text-zinc-200 mb-1 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Evidence Grounding</span>
              </h3>
              <p className="text-[11px] font-sans text-neutral-700 dark:text-zinc-400 leading-relaxed">
                DevLensX strictly answers from parsed repository tokens, AST syntax nodes, and Kùzu graph relationships. Answers will never fabricate imaginary APIs or nonexistent methods.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: WHERE SHOULD I EDIT? */}
      {activeTab === 'where-to-edit' && (
        <div className="space-y-6">
          {/* Query Box */}
          <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
            <h2 className="text-sm font-bold uppercase tracking-wider text-black dark:text-zinc-100 mb-2 flex items-center gap-2">
              <Search className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
              <span>Feature & Bug Localization Engine</span>
            </h2>
            <p className="text-xs font-sans text-neutral-600 dark:text-zinc-400 mb-4">
              Describe what feature you want to add or modify. DevLensX analyzes routing, controllers, services, repositories, and UI files to pinpoint the exact primary file, related components, step-by-step instructions, and patch preview.
            </p>

            <form
              onSubmit={e => {
                e.preventDefault();
                handleLocateEdit();
              }}
              className="flex gap-2 mb-4"
            >
              <input
                type="text"
                value={editQuery}
                onChange={e => setEditQuery(e.target.value)}
                placeholder="e.g., I want to change the login button action, or Add email alert on checkout..."
                disabled={isLocating}
                className="flex-1 px-4 py-2.5 text-xs border border-black/30 dark:border-zinc-700 bg-white dark:bg-[#0e0f12] text-black dark:text-zinc-100 placeholder:text-neutral-400 dark:placeholder:text-zinc-500 focus:outline-none focus:border-black dark:focus:border-zinc-500 shadow-sm dark:shadow-none rounded-sm"
              />
              <button
                type="submit"
                disabled={isLocating || !editQuery.trim()}
                className="px-6 py-2.5 border border-indigo-700 dark:border-indigo-500 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold uppercase disabled:opacity-40 shadow-sm dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all rounded-sm flex items-center gap-1.5"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{isLocating ? 'Locating...' : 'Locate Code'}</span>
              </button>
            </form>

            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mr-1">
                Sample Scenarios:
              </span>
              {whereToEditPresets.map((preset, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setEditQuery(preset);
                    handleLocateEdit(preset);
                  }}
                  className="text-[11px] font-sans px-2 py-1 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] hover:bg-neutral-200 dark:hover:bg-zinc-800 text-black dark:text-zinc-300 transition-colors rounded-sm"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Results Display */}
          {editResult && (
            <div className="space-y-6">
              {/* Primary File Card */}
              <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-4 border-b border-black/20 dark:border-zinc-800">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 border border-black dark:border-zinc-700 bg-black dark:bg-zinc-800 text-white dark:text-zinc-200 mr-2 rounded-sm">
                      AUTHORITATIVE PRIMARY FILE
                    </span>
                    <span className="text-xs font-bold uppercase text-neutral-500 dark:text-zinc-400">
                      Stereotype: {editResult.primary_file.stereotype}
                    </span>
                    <h3 className="text-lg font-bold text-black dark:text-zinc-100 mt-1 font-mono">
                      {editResult.primary_file.path}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold px-2 py-1 border border-black/20 dark:border-zinc-700 bg-neutral-100 dark:bg-[#181920] text-black dark:text-zinc-300 rounded-sm">
                      Lines {editResult.primary_file.line_start} - {editResult.primary_file.line_end}
                    </span>
                  </div>
                </div>

                <div className="mt-4 space-y-4 font-sans text-xs">
                  <div>
                    <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                      Why modify this component?
                    </h4>
                    <p className="text-neutral-700 dark:text-zinc-300 leading-relaxed">{editResult.explanation}</p>
                  </div>

                  {/* Exact Steps */}
                  <div>
                    <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-2">
                      Step-by-Step Implementation Instructions
                    </h4>
                    <div className="space-y-1.5">
                      {editResult.exact_instructions.map((step, idx) => (
                        <div
                          key={idx}
                          className="p-2 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] flex items-start gap-2 rounded-sm"
                        >
                          <CornerDownRight className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-neutral-500 dark:text-zinc-400" />
                          <span className="text-neutral-800 dark:text-zinc-200">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Dependency Chain & Risks */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    <div className="border border-black/20 dark:border-zinc-800 p-3 bg-neutral-50 dark:bg-[#16171d] rounded-sm">
                      <h5 className="font-bold uppercase tracking-wider font-mono text-[10px] text-black dark:text-zinc-100 mb-2 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-zinc-600 dark:text-zinc-400" />
                        <span>Dependency Call Chain</span>
                      </h5>
                      <div className="space-y-1">
                        {editResult.dependency_chain.map((chain, i) => (
                          <div key={i} className="text-[11px] font-mono text-neutral-700 dark:text-zinc-300">
                            {i > 0 ? '→ ' : ''}{chain}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="border border-black/20 dark:border-zinc-800 p-3 bg-neutral-50 dark:bg-[#16171d] rounded-sm">
                      <h5 className="font-bold uppercase tracking-wider font-mono text-[10px] text-black dark:text-zinc-100 mb-2 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-zinc-600 dark:text-zinc-400" />
                        <span>Risk & Downstream Blast Radius</span>
                      </h5>
                      <div className="text-[11px] space-y-1 text-neutral-700 dark:text-zinc-300 font-mono">
                        <div>Risk Level: <span className="font-bold">{editResult.risks_and_impact.risk_level}</span></div>
                        <div>Affected Callers: {editResult.risks_and_impact.downstream_callers.join(', ') || 'Self-contained'}</div>
                        <div>Tests to Run: {editResult.risks_and_impact.tests_to_run.join(', ')}</div>
                      </div>
                    </div>
                  </div>

                  {/* Related Files */}
                  {editResult.related_files.length > 0 && (
                    <div>
                      <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-2">
                        Related Files to Inspect & Update
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {editResult.related_files.map((rf, idx) => (
                          <div key={idx} className="p-2 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] rounded-sm">
                            <div className="font-mono font-bold text-xs text-black dark:text-zinc-200">{rf.path}</div>
                            <div className="text-[10px] font-mono text-neutral-500 dark:text-zinc-400 uppercase">{rf.symbol} ({rf.role})</div>
                            <div className="text-[11px] text-neutral-600 dark:text-zinc-400 mt-1">{rf.reason}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Patch Preview */}
                  {editResult.patch_preview && (
                    <div>
                      <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                        Suggested Unified Diff Patch Preview
                      </h4>
                      <pre className="p-3 border border-black/20 dark:border-zinc-800 bg-neutral-950 text-zinc-100 font-mono text-xs overflow-x-auto rounded-sm leading-relaxed">
                        {editResult.patch_preview.split('\n').map((l, idx) => {
                          if (l.startsWith('+') && !l.startsWith('+++')) {
                            return <div key={idx} className="text-emerald-400 bg-emerald-950/30 px-1">{l}</div>;
                          }
                          if (l.startsWith('-') && !l.startsWith('---')) {
                            return <div key={idx} className="text-rose-400 bg-rose-950/30 px-1">{l}</div>;
                          }
                          if (l.startsWith('@@')) {
                            return <div key={idx} className="text-sky-400 font-bold">{l}</div>;
                          }
                          return <div key={idx} className="text-zinc-300">{l}</div>;
                        })}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: EXPLAIN CONCEPTS */}
      {activeTab === 'explain' && (
        <div className="space-y-6">
          <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
            <h2 className="text-sm font-bold uppercase tracking-wider text-black dark:text-zinc-100 mb-2 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
              <span>Contextual Concept Explanations (4-Part Framework)</span>
            </h2>
            <p className="text-xs font-sans text-neutral-600 dark:text-zinc-400 mb-4">
              Learn how any technology or framework is used specifically in this repository:
              1. What it is, 2. Why it is used, 3. How this repository uses it, and 4. Where it is implemented with file links.
            </p>

            <form
              onSubmit={e => {
                e.preventDefault();
                handleExplain();
              }}
              className="flex gap-2 mb-4"
            >
              <input
                type="text"
                value={conceptQuery}
                onChange={e => setConceptQuery(e.target.value)}
                placeholder="e.g., Gemini, RAG, FAISS, Postgres, Spring, Redis..."
                disabled={isExplaining}
                className="flex-1 px-4 py-2.5 text-xs border border-black/30 dark:border-zinc-700 bg-white dark:bg-[#0e0f12] text-black dark:text-zinc-100 placeholder:text-neutral-400 dark:placeholder:text-zinc-500 focus:outline-none focus:border-black dark:focus:border-zinc-500 shadow-sm dark:shadow-none rounded-sm"
              />
              <button
                type="submit"
                disabled={isExplaining || !conceptQuery.trim()}
                className="px-6 py-2.5 border border-violet-700 dark:border-violet-500 bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold uppercase disabled:opacity-40 shadow-sm dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all rounded-sm flex items-center gap-1.5"
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>{isExplaining ? 'Explaining...' : 'Explain Concept'}</span>
              </button>
            </form>

            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mr-1">
                Explore Technology:
              </span>
              {conceptPresets.map((c, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setConceptQuery(c);
                    handleExplain(c);
                  }}
                  className="text-[11px] font-sans px-2.5 py-1 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] hover:bg-neutral-200 dark:hover:bg-zinc-800 text-black dark:text-zinc-300 transition-colors rounded-sm"
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {conceptResult && (
            <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black/20 dark:border-zinc-800">
                <h3 className="text-lg font-bold uppercase tracking-tight text-black dark:text-zinc-100 font-mono">
                  Concept: {conceptResult.concept}
                </h3>
                <span className="text-xs font-bold px-2 py-0.5 border border-black/20 dark:border-zinc-700 bg-neutral-100 dark:bg-[#181920] text-black dark:text-zinc-300 rounded-sm">
                  {conceptResult.verdict}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
                <div className="p-4 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] rounded-sm">
                  <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                    1. What It Is
                  </h4>
                  <p className="text-neutral-700 dark:text-zinc-300 leading-relaxed">{conceptResult.what}</p>
                </div>

                <div className="p-4 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] rounded-sm">
                  <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                    2. Why It Is Used
                  </h4>
                  <p className="text-neutral-700 dark:text-zinc-300 leading-relaxed">{conceptResult.why}</p>
                </div>

                <div className="p-4 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] rounded-sm">
                  <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                    3. How This Repository Uses It
                  </h4>
                  <p className="text-neutral-700 dark:text-zinc-300 leading-relaxed">{conceptResult.how}</p>
                </div>

                <div className="p-4 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] rounded-sm">
                  <h4 className="font-bold uppercase tracking-wider text-black dark:text-zinc-100 font-mono text-[11px] mb-1">
                    4. Where It Is Implemented
                  </h4>
                  <div className="space-y-1 mt-2">
                    {conceptResult.where.map((loc, idx) => (
                      <div key={idx} className="font-mono text-xs text-black dark:text-zinc-200 border-b border-neutral-200 dark:border-zinc-800/80 pb-1">
                        - `{loc}`
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: CHANGE IMPACT */}
      {activeTab === 'blast-radius' && (
        <div className="space-y-6">
          <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm">
            <h2 className="text-sm font-bold uppercase tracking-wider text-black dark:text-zinc-100 mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
              <span>Blast Radius & Caller Graph Inspection</span>
            </h2>
            <p className="text-xs font-sans text-neutral-600 dark:text-zinc-400 mb-4">
              Evaluate which downstream components will be broken or affected if you modify a specific class.
            </p>

            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={targetClass}
                onChange={e => setTargetClass(e.target.value)}
                placeholder="Target class name (e.g. OwnerController, ClinicService)..."
                disabled={isCalculatingBlast}
                className="flex-1 px-4 py-2.5 text-xs border border-black/30 dark:border-zinc-700 bg-white dark:bg-[#0e0f12] text-black dark:text-zinc-100 placeholder:text-neutral-400 dark:placeholder:text-zinc-500 focus:outline-none focus:border-black dark:focus:border-zinc-500 shadow-sm dark:shadow-none rounded-sm"
              />
              <button
                onClick={handleCalculateBlast}
                disabled={isCalculatingBlast || !targetClass.trim()}
                className="px-6 py-2.5 border border-amber-600 bg-amber-500 hover:bg-amber-400 text-black text-xs font-black uppercase disabled:opacity-40 shadow-sm dark:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-all rounded-sm flex items-center gap-1.5"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{isCalculatingBlast ? 'Calculating...' : 'Calculate Blast Radius'}</span>
              </button>
            </div>
          </div>

          {blastResult && (
            <div className="border border-black dark:border-[#26272e] bg-white dark:bg-[#121316] p-6 shadow-sm dark:shadow-none rounded-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black/20 dark:border-zinc-800">
                <h3 className="text-sm font-bold uppercase tracking-wider text-black dark:text-zinc-100">
                  Blast Radius: {blastResult.target_class || targetClass}
                </h3>
                <span className="text-xs font-bold px-2 py-0.5 border border-black dark:border-zinc-700 bg-black dark:bg-zinc-800 text-white dark:text-zinc-200 rounded-sm">
                  Risk: {blastResult.risk_level || 'MEDIUM'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-3 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] text-center rounded-sm">
                  <div className="text-2xl font-bold text-black dark:text-zinc-100">{blastResult.direct_callers?.length || 0}</div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mt-1">Direct Callers</div>
                </div>
                <div className="p-3 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] text-center rounded-sm">
                  <div className="text-2xl font-bold text-black dark:text-zinc-100">{blastResult.impact?.potentially_affected || 0}</div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mt-1">Potentially Affected</div>
                </div>
                <div className="p-3 border border-black/20 dark:border-zinc-800 bg-neutral-50 dark:bg-[#16171d] text-center rounded-sm">
                  <div className="text-2xl font-bold text-black dark:text-zinc-100">{blastResult.status || 'ANALYZED'}</div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-zinc-400 mt-1">Graph Verdict</div>
                </div>
              </div>

              {blastResult.direct_callers && blastResult.direct_callers.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-black dark:text-zinc-100 mb-2">
                    Direct Upstream Callers
                  </h4>
                  <div className="space-y-1">
                    {blastResult.direct_callers.map((c: string, idx: number) => (
                      <div key={idx} className="p-2 border border-black/20 dark:border-zinc-800 bg-white dark:bg-[#16171d] text-xs flex items-center justify-between rounded-sm">
                        <span className="font-bold text-black dark:text-zinc-200">{c}</span>
                        <span className="text-[10px] uppercase text-neutral-500 dark:text-zinc-400">DEPENDENT CALLER</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
