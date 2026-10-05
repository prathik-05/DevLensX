import React from "react";
export const StatusIndicator: React.FC<{status: string; message?: string}> = ({status, message}) => {
  const color = status==="READY" ? "text-emerald-400" : status==="FAILED" ? "text-rose-400" : status==="STALE" ? "text-amber-400" : "text-slate-400";
  return <div className={`px-2 py-0.5 rounded text-xs font-mono ${color} border border-slate-700 bg-slate-900`}>{status}{message?`: ${message}`:""}</div>;
};
