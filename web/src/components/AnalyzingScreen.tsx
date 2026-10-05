import React from 'react';
import { Bot, Sparkles, Cpu, GitBranch, Shield } from 'lucide-react';

interface AnalyzingScreenProps {
  repoPath: string;
}

export const AnalyzingScreen: React.FC<AnalyzingScreenProps> = ({ repoPath }) => {
  return (
    <div className="min-h-screen bg-white dark:bg-[#0a0a0f] text-[#0f172a] dark:text-[#f8fafc] flex flex-col items-center justify-center p-6 selection:bg-[#00ff88] selection:text-black font-sans">
      <div className="max-w-md w-full text-center space-y-6 bg-white dark:bg-[#12131a] p-8 border-2 border-black dark:border-slate-800 shadow-[6px_6px_0px_0px_#000000]">
        <div className="w-16 h-16 mx-auto bg-black text-white flex items-center justify-center border-2 border-black shadow-[3px_3px_0px_0px_#00ff88]">
          <Bot className="w-8 h-8 text-[#00ff88]" />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-center space-x-1.5 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#0284c7]" />
            <span className="w-2 h-2 rounded-none bg-[#c026d3]" />
            <span className="w-2 h-2 bg-[#d97706]" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
          </div>
          <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight">Understanding Repository</h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-mono truncate px-4 font-bold">{repoPath}</p>
        </div>

        {/* Conversational Staged Progress Indicators */}
        <div className="space-y-2.5 text-left font-mono text-xs">
          <div className="flex items-center space-x-3 p-3 bg-sky-50 dark:bg-sky-950/40 border-2 border-black dark:border-sky-500">
            <div className="w-4 h-4 border-2 border-[#0284c7] border-t-transparent rounded-full animate-spin shrink-0" />
            <span className="text-[#0284c7] font-bold">Extracting AST AST signatures & annotations...</span>
          </div>

          <div className="flex items-center space-x-3 p-3 bg-slate-50 dark:bg-[#181824] border-2 border-black dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium">
            <Cpu className="w-4 h-4 text-[#7c3aed] shrink-0" />
            <span>Building Cypher property graph relationships...</span>
          </div>

          <div className="flex items-center space-x-3 p-3 bg-slate-50 dark:bg-[#181824] border-2 border-black dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium">
            <GitBranch className="w-4 h-4 text-[#059669] shrink-0" />
            <span>Indexing FAISS dense vector embeddings...</span>
          </div>

          <div className="flex items-center space-x-3 p-3 bg-slate-50 dark:bg-[#181824] border-2 border-black dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium">
            <Shield className="w-4 h-4 text-[#d97706] shrink-0" />
            <span>Preparing AI Senior Architect Onboarding...</span>
          </div>
        </div>

        <div className="pt-2 border-t-2 border-black dark:border-slate-800">
          <span className="text-[11px] text-black dark:text-white font-mono font-bold flex items-center justify-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#0284c7]" />
            <span>Synthesizing 30-Second AI Architect Overview</span>
          </span>
        </div>
      </div>
    </div>
  );
};
