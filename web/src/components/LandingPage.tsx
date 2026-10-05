import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Link2, FolderOpen, Play, ArrowRight, Cpu, Network, ShieldCheck, Sparkles } from 'lucide-react';
import { Badge } from './Badge';
import { TerminalWindow, type TerminalAccent } from './TerminalWindow';
import { ThemeToggle } from './ThemeToggle';
import { useAppStore } from '../store';

type InputMode = 'url' | 'path' | 'zip';

const MODE_TABS: Array<{ id: InputMode; label: string; icon: React.ComponentType<{ className?: string }>; accent: TerminalAccent }> = [
  { id: 'url', label: 'GitHub URL', icon: Link2, accent: 'cyan' },
  { id: 'path', label: 'Local Path', icon: FolderOpen, accent: 'green' },
  { id: 'zip', label: 'Upload .zip', icon: Upload, accent: 'magenta' },
];

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const repoPath = useAppStore(s => s.repoPath);
  const setRepoPath = useAppStore(s => s.setRepoPath);
  const runAnalysis = useAppStore(s => s.runAnalysis);
  const uploadAndAnalyze = useAppStore(s => s.uploadAndAnalyze);
  const isAnalyzing = useAppStore(s => s.isAnalyzing);
  const analysisError = useAppStore(s => s.analysisError);
  const [mode, setMode] = useState<InputMode>('url');
  const [activeCommand, setActiveCommand] = useState<number | null>(null);

  const startAnalysis = async () => {
    const data = await runAnalysis(repoPath);
    if (data) navigate('/overview');
  };

  const handleZip = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const data = await uploadAndAnalyze(e.target.files[0]);
      e.target.value = '';
      if (data) navigate('/overview');
    }
  };

  const commands = [
    { id: 1, cmd: 'ANALYZE', desc: 'Execute AST parse & build knowledge graph', action: () => document.getElementById('repo-input-section')?.scrollIntoView({ behavior: 'smooth' }) },
    { id: 2, cmd: 'SEARCH', desc: 'Query codebase entities & call chains', action: () => navigate('/overview') },
    { id: 3, cmd: 'INSPECT', desc: 'Launch CodeTurtle AST-grounded review', action: () => navigate('/code-turtle') },
    { id: 4, cmd: 'VISUALIZE', desc: 'Browse RepoMind Living Architecture Wiki', action: () => navigate('/wiki') },
    { id: 5, cmd: 'EVALUATE', desc: 'Run ground-truth telemetry diagnostic', action: () => navigate('/evaluation') },
  ];

  return (
    <div className="min-h-screen bg-[#f8fafc] text-[#0f172a] font-sans cyber-grid selection:bg-[#10b981] selection:text-white">
      {/* Top OS Command Bar */}
      <header className="border-b-2 border-black bg-white px-6 py-3.5 flex items-center justify-between shadow-[0_2px_0_0_#000000] sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#0284c7]" title="Circle" />
            <span className="w-2.5 h-2.5 rounded-none bg-[#c026d3]" title="Square" />
            <span
              className="w-2.5 h-2.5 bg-[#d97706]"
              style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
              title="Triangle"
            />
          </div>
          <span className="font-sans text-sm font-black tracking-wider text-black uppercase">
            DEVLENSX://CORE
          </span>
          <span className="hidden sm:inline-block px-2 py-0.5 text-[9px] font-sans font-bold uppercase tracking-wider bg-[#059669]/10 text-[#059669] border border-[#059669]">
            SYS://READY
          </span>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <button
            onClick={() => navigate('/overview')}
            className="px-3 py-1.5 text-xs font-sans font-bold uppercase border-2 border-black bg-white text-black hover:bg-neutral-100 shadow-[2px_2px_0px_0px_#000000] transition-all cursor-pointer"
          >
            WORKSPACE
          </button>
          <button
            onClick={() => navigate('/wiki')}
            className="px-3 py-1.5 text-xs font-sans font-bold uppercase border-2 border-black bg-white text-[#0284c7] hover:bg-neutral-100 shadow-[2px_2px_0px_0px_#000000] transition-all cursor-pointer"
          >
            WIKI
          </button>
        </div>
      </header>

      {/* Main Constructivist Poster Canvas */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-12">
        {/* HERO BOOT SEQUENCE (60/40 ASYMMETRIC GRID) */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative">
          {/* Hero Left: 60% Typography & Boot Stream */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white text-black border-2 border-black text-xs font-sans font-bold uppercase tracking-wider shadow-[3px_3px_0px_0px_#000000]">
              <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
              <span>SYS://BOOT_SEQUENCE</span>
              <span className="text-neutral-400">•</span>
              <span className="text-[#0284c7]">POLYGLOT URM</span>
            </div>

            <h1 className="text-5xl sm:text-7xl lg:text-8xl font-black uppercase tracking-tight leading-[0.95] text-black font-sans">
              SYSTEM <br />
              <span className="text-[#0284c7]">INTELLIGENCE</span> <br />
              <span className="text-[#059669]">ONLINE</span>
            </h1>

            {/* Terminal Boot Log */}
            <div className="p-4 bg-[#09090b] border-2 border-black shadow-[5px_5px_0px_0px_#000000] text-xs font-mono space-y-1 text-neutral-300">
              <div className="text-[#10b981]">&gt; initializing repository intelligence...</div>
              <div className="text-[#38bdf8]">&gt; loading Tree-sitter AST parser &amp; language adapters...</div>
              <div className="text-[#38bdf8]">&gt; connecting Kùzu embedded property graph &amp; FAISS index...</div>
              <div className="text-[#fbbf24]">&gt; verifying evidence threshold via ClaimVerifier...</div>
              <div className="text-[#10b981] font-bold flex items-center gap-1">
                <span>&gt; system ready</span>
                <span className="animate-blink text-[#10b981]">█</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <Badge variant="verified" size="md">Multi-Language URM</Badge>
              <Badge variant="finding-arch" size="md">AST Grounded</Badge>
              <Badge variant="finding-impact" size="md">Blast Radius</Badge>
              <Badge variant="ai-suggestion" size="md">Code Turtle</Badge>
            </div>

            <div className="flex flex-wrap gap-3 pt-4">
              <button
                onClick={() => document.getElementById('repo-input-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-5 py-2.5 text-xs font-sans font-bold uppercase tracking-wider bg-[#10b981] text-black border-2 border-black hover:bg-[#059669] hover:text-white shadow-[4px_4px_0px_0px_#000000] active:translate-x-[2px] active:translate-y-[2px] transition-all flex items-center gap-2"
              >
                <span>INITIALIZE ANALYSIS</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => navigate('/wiki')}
                className="px-5 py-2.5 text-xs font-sans font-bold uppercase tracking-wider bg-white text-black border-2 border-black hover:bg-neutral-100 hover:text-[#0284c7] shadow-[4px_4px_0px_0px_#000000] active:translate-x-[2px] active:translate-y-[2px] transition-all"
              >
                EXPLORE REPOSITORY WIKI
              </button>
            </div>
          </div>

          {/* Hero Right: 40% Large Interactive Terminal Window with Bauhaus Geometry */}
          <div className="lg:col-span-5 relative">
            {/* Background Bauhaus Geometric Composition (Low Opacity) */}
            <div className="absolute -top-8 -right-8 w-64 h-64 rounded-full bg-[#00d4ff]/10 border border-[#00d4ff]/30 shadow-[8px_8px_0px_0px_#000000] pointer-events-none" />
            <div className="absolute -bottom-6 -left-6 w-48 h-48 bg-[#ff00ff]/10 border border-[#ff00ff]/30 rotate-12 shadow-[8px_8px_0px_0px_#000000] pointer-events-none" />
            <div className="absolute top-1/2 -right-4 w-32 h-6 bg-[#f0c020]/20 border border-[#f0c020]/40 shadow-[4px_4px_0px_0px_#000000] pointer-events-none" />

            {/* Central Terminal Window */}
            <TerminalWindow
              title="DEVLENSX://CORE"
              status="ONLINE"
              pid="0421"
              accent="green"
              className="relative z-10"
            >
              <div className="space-y-3 font-mono text-xs">
                <div className="text-[#6b7280] pb-2 border-b border-[#2a2a3a]">
                  SYSTEM STATUS TELEMETRY
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e0e0]">CORE RUNTIME</span>
                    <span className="text-[#00ff88] font-bold">[ONLINE]</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e0e0]">AST PARSER (TREE-SITTER)</span>
                    <span className="text-[#00d4ff] font-bold">[READY]</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e0e0]">KNOWLEDGE GRAPH (KÙZU)</span>
                    <span className="text-[#00d4ff] font-bold">[READY]</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e0e0]">HYBRID GRAPHRAG</span>
                    <span className="text-[#00ff88] font-bold">[ACTIVE]</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e0e0]">CLAIM VERIFIER</span>
                    <span className="text-[#f0c020] font-bold">[ONLINE]</span>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="flex justify-between text-[11px] text-[#6b7280] mb-1">
                    <span>INDEX PROCESS</span>
                    <span className="text-[#00ff88]">94%</span>
                  </div>
                  <div className="w-full bg-[#0e0e16] border border-[#2a2a3a] h-3 p-0.5">
                    <div className="bg-[#00ff88] h-full w-[94%] shadow-[0_0_8px_#00ff88]" />
                  </div>
                </div>

                <div className="pt-2 text-[#00ff88] flex items-center gap-1">
                  <span>&gt; awaiting command</span>
                  <span className="animate-blink">█</span>
                </div>
              </div>
            </TerminalWindow>
          </div>
        </section>

        {/* TELEMETRY WALL (SECTION 12 & 16) */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border-2 border-black p-5 relative shadow-[4px_4px_0px_0px_#000000] overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-[#0284c7]/10 rounded-full -mr-8 -mt-8" />
            <div className="font-sans text-3xl sm:text-4xl font-black text-[#0284c7] tracking-tight mb-1">1,284</div>
            <div className="font-sans text-xs font-bold uppercase tracking-wider text-neutral-500">FILES INDEXED</div>
            <div className="mt-2 text-[11px] font-sans font-medium text-[#0284c7]">Java • TypeScript • Python AST</div>
          </div>

          <div className="bg-white border-2 border-black p-5 relative shadow-[4px_4px_0px_0px_#000000] overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-[#059669]/10 rotate-12 -mr-8 -mt-8" />
            <div className="font-sans text-3xl sm:text-4xl font-black text-[#059669] tracking-tight mb-1">98.7%</div>
            <div className="font-sans text-xs font-bold uppercase tracking-wider text-neutral-500">GROUNDING ACCURACY</div>
            <div className="mt-2 text-[11px] font-sans font-medium text-[#059669]">ClaimVerifier AST-bounded</div>
          </div>

          <div className="bg-white border-2 border-black p-5 relative shadow-[4px_4px_0px_0px_#000000] overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-[#c026d3]/10 -mr-8 -mt-8" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
            <div className="font-sans text-3xl sm:text-4xl font-black text-[#c026d3] tracking-tight mb-1">0421</div>
            <div className="font-sans text-xs font-bold uppercase tracking-wider text-neutral-500">AST SYMBOLS</div>
            <div className="mt-2 text-[11px] font-sans font-medium text-[#c026d3]">Kùzu Graph Relations &amp; Triples</div>
          </div>
        </section>

        {/* REPOSITORY INPUT COMMAND CENTER (SECTION 10) */}
        <section id="repo-input-section" className="border-2 border-black bg-white p-6 sm:p-8 shadow-[6px_6px_0px_0px_#000000] relative">
          <div className="absolute top-3 right-3 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#0284c7]" />
            <span className="w-2.5 h-2.5 bg-[#c026d3]" />
            <span className="w-2.5 h-2.5 bg-[#d97706]" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className="w-2 h-8 bg-[#10b981]" />
            <div>
              <h2 className="text-xl sm:text-2xl font-black font-sans uppercase tracking-tight text-black">ANALYZE A REPOSITORY</h2>
              <p className="text-xs font-sans uppercase tracking-wider text-neutral-500">Command Console Pipeline (Tree-sitter → URM → Kùzu → GraphRAG → ClaimVerifier)</p>
            </div>
          </div>

          {/* Mode Selector Tabs */}
          <div className="flex flex-wrap gap-2 mb-6" role="tablist" aria-label="Repository source">
            {MODE_TABS.map(tab => {
              const Icon = tab.icon;
              const active = mode === tab.id;
              const tabColor = tab.accent === 'cyan' ? 'text-[#0284c7]' : tab.accent === 'green' ? 'text-[#059669]' : 'text-[#c026d3]';
              const tabBg = tab.accent === 'cyan' ? 'bg-[#0284c7]/15' : tab.accent === 'green' ? 'bg-[#059669]/15' : 'bg-[#c026d3]/15';

              return (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setMode(tab.id)}
                  disabled={isAnalyzing}
                  className={`px-4 py-2 text-xs font-sans font-bold uppercase transition-all border-2 border-black ${
                    active
                      ? `${tabColor} ${tabBg} shadow-[3px_3px_0px_0px_#000000]`
                      : 'bg-white text-neutral-600 hover:text-black hover:bg-neutral-50'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </span>
                </button>
              );
            })}
          </div>

          {/* Input or File Upload */}
          {mode === 'zip' ? (
            <label className="w-full p-8 border-2 border-dashed border-black bg-neutral-50 hover:bg-neutral-100 flex flex-col items-center justify-center gap-3 cursor-pointer shadow-[3px_3px_0px_0px_#000000] transition-colors">
              <div className="w-12 h-12 bg-white border-2 border-black flex items-center justify-center shadow-[2px_2px_0px_0px_#000000]">
                <Upload className="w-6 h-6 text-[#c026d3]" />
              </div>
              <span className="text-sm font-sans font-bold uppercase tracking-wider text-black">
                {isAnalyzing ? 'UPLOADING AND ANALYZING…' : 'CHOOSE A .ZIP ARCHIVE OF THE REPOSITORY'}
              </span>
              <span className="text-xs font-sans text-neutral-500">Limit 50MB • Path-traversal protected</span>
              <input type="file" accept=".zip" onChange={handleZip} className="hidden" disabled={isAnalyzing} />
            </label>
          ) : (
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-black font-bold">&gt;</span>
                <input
                  type="text"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') startAnalysis(); }}
                  placeholder="https://github.com/owner/repo or eval_repos/spring-petclinic"
                  disabled={isAnalyzing}
                  className="w-full pl-8 pr-4 py-2.5 text-xs font-mono bg-white border-2 border-black text-black placeholder-neutral-400 focus:outline-none shadow-[3px_3px_0px_0px_#000000] rounded-none"
                />
              </div>

              <button
                onClick={startAnalysis}
                disabled={isAnalyzing || !repoPath.trim()}
                className="px-6 py-2.5 text-xs font-sans font-bold uppercase tracking-wider bg-[#10b981] text-black border-2 border-black hover:bg-[#059669] hover:text-white shadow-[4px_4px_0px_0px_#000000] active:translate-x-[2px] active:translate-y-[2px] transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                    <span>ANALYZING...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>EXECUTE ANALYSIS</span>
                  </>
                )}
              </button>
            </div>
          )}

          {analysisError && (
            <div className="mt-4 p-3 border-2 border-[#dc2626] bg-[#dc2626]/10 text-[#dc2626] text-xs font-mono font-bold">
              [ERROR] {analysisError}
            </div>
          )}
        </section>

        {/* TERMINAL COMMAND CENTER (SECTION 11 & 17) */}
        <section className="space-y-4">
          <TerminalWindow
            title="TERMINAL://COMMAND_CENTER"
            status="ACTIVE"
            accent="cyan"
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="text-[#00d4ff]">&gt; help</div>
              <div className="text-[#6b7280] font-bold uppercase tracking-widest pb-1 border-b border-[#2a2a3a]">
                AVAILABLE COMMANDS (CLICK OR SELECT)
              </div>

              <div className="space-y-2 pt-1">
                {commands.map((c) => {
                  const isHovered = activeCommand === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={c.action}
                      onMouseEnter={() => setActiveCommand(c.id)}
                      onMouseLeave={() => setActiveCommand(null)}
                      className={`p-2 border transition-all cursor-pointer flex items-center justify-between ${
                        isHovered
                          ? 'border-[#00d4ff] bg-[#00d4ff]/15 text-white shadow-[0_0_10px_rgba(0,212,255,0.3)]'
                          : 'border-[#2a2a3a] bg-[#0e0e16] text-[#9ca3af] hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-[#00d4ff] font-bold">[{c.id < 10 ? `0${c.id}` : c.id}]</span>
                        <span className="font-bold tracking-wider">{c.cmd}</span>
                        {isHovered && <span className="animate-blink text-[#00d4ff]">█</span>}
                      </div>
                      <span className="text-[11px] text-[#6b7280] hidden sm:inline-block">{c.desc}</span>
                    </div>
                  );
                })}
              </div>

              <div className="pt-2 text-[#6b7280] flex items-center gap-1">
                <span>&gt; _</span>
              </div>
            </div>
          </TerminalWindow>
        </section>

        {/* 4-STAGE ARCHITECTURAL PIPELINE */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-[#6b7280]">
            <span className="text-[#00ff88]">&gt;</span>
            <span>SYSTEM ARCHITECTURE PIPELINE</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <TerminalWindow title="01://URM_PARSER" status="READY" accent="green" controls={false}>
              <div className="space-y-2">
                <Cpu className="w-5 h-5 text-[#00ff88]" />
                <h3 className="font-bold text-sm text-white">Universal Repository Model</h3>
                <p className="text-xs text-[#9ca3af]">
                  Tree-sitter AST extraction normalizing symbols across Java, TypeScript, and Python.
                </p>
              </div>
            </TerminalWindow>

            <TerminalWindow title="02://GRAPH_STORE" status="READY" accent="cyan" controls={false}>
              <div className="space-y-2">
                <Network className="w-5 h-5 text-[#00d4ff]" />
                <h3 className="font-bold text-sm text-white">Kùzu Property Graph</h3>
                <p className="text-xs text-[#9ca3af]">
                  High-speed embedded C++ graph storage executing Cypher call graphs and blast-radius traversal.
                </p>
              </div>
            </TerminalWindow>

            <TerminalWindow title="03://GRAPHRAG" status="ACTIVE" accent="magenta" controls={false}>
              <div className="space-y-2">
                <Sparkles className="w-5 h-5 text-[#ff00ff]" />
                <h3 className="font-bold text-sm text-white">Hybrid GraphRAG</h3>
                <p className="text-xs text-[#9ca3af]">
                  Coordinates structural graph paths, FAISS dense vectors, and deterministic AST excerpts.
                </p>
              </div>
            </TerminalWindow>

            <TerminalWindow title="04://VERIFIER" status="ONLINE" accent="yellow" controls={false}>
              <div className="space-y-2">
                <ShieldCheck className="w-5 h-5 text-[#f0c020]" />
                <h3 className="font-bold text-sm text-white">ClaimVerifier</h3>
                <p className="text-xs text-[#9ca3af]">
                  Fail-closed boundary verifying line-level citations and enforcing strict claim separation.
                </p>
              </div>
            </TerminalWindow>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-6 py-6 mt-16 text-xs font-mono text-slate-500 dark:text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
          <span className="text-slate-900 dark:text-slate-100 font-bold">DEVLENSX</span>
          <span>•</span>
          <span>AI REPOSITORY REASONING ENGINE</span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono font-medium text-slate-600 dark:text-slate-400">
          <span>ZERO HALLUCINATIONS</span>
          <span>•</span>
          <span>EVIDENCE-BACKED PROVENANCE</span>
        </div>
      </footer>
    </div>
  );
};