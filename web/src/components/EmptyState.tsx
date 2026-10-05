import React from "react";

export const EmptyState: React.FC<{title: string; message: string; action?: React.ReactNode}> = ({title, message, action}) => (
  <div className="p-8 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-800 shadow-[3px_3px_0px_0px_#000000] text-center space-y-2">
    <div className="text-black dark:text-white font-black text-sm uppercase tracking-wider">{title}</div>
    <div className="text-slate-700 dark:text-slate-300 text-xs font-medium">{message}</div>
    {action}
  </div>
);

export const LoadingState: React.FC<{message?: string}> = ({message="Analyzing repository..."}) => (
  <div className="p-6 bg-white dark:bg-[#12131a] border-2 border-black dark:border-slate-800 shadow-[3px_3px_0px_0px_#000000] text-center animate-pulse">
    <div className="text-[#0284c7] font-mono text-xs font-bold">{message}</div>
    <div className="mt-2 text-slate-700 dark:text-slate-300 text-xs font-medium">✓ Repository discovered · Parsing source files · Building dependency graph · Generating documentation</div>
  </div>
);

export const StaleState: React.FC<{current?: string, analyzed?: string, onReanalyze?: ()=>void}> = ({current, analyzed, onReanalyze}) => (
  <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border-2 border-black dark:border-amber-800 shadow-[3px_3px_0px_0px_#000000] space-y-2">
    <div className="text-amber-900 dark:text-amber-300 font-black text-xs uppercase">⚠ Workspace is stale.</div>
    <div className="text-slate-800 dark:text-slate-300 text-xs font-mono font-medium">Current commit: {current || "unknown"} / Analyzed commit: {analyzed || "unknown"}</div>
    <button onClick={onReanalyze} disabled={!onReanalyze} className="px-3 py-1.5 bg-black hover:bg-slate-800 text-white font-bold text-xs border-2 border-black shadow-[2px_2px_0px_0px_#000000] disabled:opacity-40 disabled:cursor-not-allowed">Re-analyze Repository</button>
  </div>
);

