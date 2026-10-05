import React from 'react';

export type TerminalAccent = 'green' | 'cyan' | 'magenta' | 'yellow' | 'red' | 'blue';

interface TerminalWindowProps {
  title?: string;
  status?: string;
  pid?: string;
  accent?: TerminalAccent;
  chamfer?: boolean;
  className?: string;
  children?: React.ReactNode;
  controls?: boolean;
}

const ACCENT_STYLES: Record<TerminalAccent, {
  border: string;
  glow: string;
  titleColor: string;
  lineColor: string;
  statusBg: string;
  statusText: string;
}> = {
  green: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(16,185,129,0.25)]',
    titleColor: 'text-[#10b981]',
    lineColor: 'bg-[#10b981]',
    statusBg: 'bg-[#10b981]/20',
    statusText: 'text-[#10b981]',
  },
  cyan: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(2,132,199,0.25)]',
    titleColor: 'text-[#38bdf8]',
    lineColor: 'bg-[#0284c7]',
    statusBg: 'bg-[#0284c7]/20',
    statusText: 'text-[#38bdf8]',
  },
  magenta: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(192,38,211,0.25)]',
    titleColor: 'text-[#e879f9]',
    lineColor: 'bg-[#c026d3]',
    statusBg: 'bg-[#c026d3]/20',
    statusText: 'text-[#e879f9]',
  },
  yellow: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(217,119,6,0.25)]',
    titleColor: 'text-[#fbbf24]',
    lineColor: 'bg-[#d97706]',
    statusBg: 'bg-[#d97706]/20',
    statusText: 'text-[#fbbf24]',
  },
  red: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(220,38,38,0.25)]',
    titleColor: 'text-[#f87171]',
    lineColor: 'bg-[#dc2626]',
    statusBg: 'bg-[#dc2626]/20',
    statusText: 'text-[#f87171]',
  },
  blue: {
    border: 'border-black',
    glow: 'hover:shadow-[0_0_15px_rgba(37,99,235,0.3)]',
    titleColor: 'text-[#60a5fa]',
    lineColor: 'bg-[#2563eb]',
    statusBg: 'bg-[#2563eb]/20',
    statusText: 'text-[#60a5fa]',
  },
};

export const TerminalWindow: React.FC<TerminalWindowProps> = ({
  title = 'CORE://TERMINAL',
  status = 'ONLINE',
  pid,
  accent = 'green',
  chamfer = true,
  className = '',
  children,
  controls = true,
}) => {
  const cfg = ACCENT_STYLES[accent] || ACCENT_STYLES.green;

  return (
    <div
      data-terminal="true"
      className={`terminal-window terminal-dark bg-[#09090b] text-white border-2 border-black shadow-[6px_6px_0px_0px_#000000] ${cfg.glow} transition-all duration-150 relative ${
        chamfer ? 'cyber-chamfer' : 'rounded-none'
      } ${className}`}
    >
      {/* Terminal Window Masthead */}
      <div className="px-4 py-2.5 bg-[#18181b] border-b-2 border-black flex items-center justify-between select-none">
        {/* Left: Traffic Lights + System Title */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] inline-block shadow-[0_0_4px_#ef4444]" title="Close" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] inline-block shadow-[0_0_4px_#f59e0b]" title="Minimize" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] inline-block shadow-[0_0_4px_#10b981]" title="Maximize" />
          </div>

          <div className="flex items-center gap-2">
            <span className={`font-mono text-xs font-black tracking-wider uppercase ${cfg.titleColor}`}>
              {title}
            </span>
            {pid && (
              <span className="text-[10px] font-mono text-neutral-400 hidden sm:inline-block">
                PID:{pid}
              </span>
            )}
          </div>
        </div>

        {/* Right: Status Pill & Controls */}
        <div className="flex items-center gap-3">
          {status && (
            <span
              className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider border border-current ${cfg.statusBg} ${cfg.statusText}`}
            >
              [{status}]
            </span>
          )}

          {controls && (
            <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono text-[#6b7280]">
              <span className="hover:text-white cursor-pointer px-1">[—]</span>
              <span className="hover:text-white cursor-pointer px-1">[□]</span>
              <span className="hover:text-[#ff3366] cursor-pointer px-1">[×]</span>
            </div>
          )}
        </div>
      </div>

      {/* Decorative Accent Line Under Header */}
      <div className={`h-[2px] w-full ${cfg.lineColor}`} />

      {/* Terminal Body Content */}
      <div className="p-4 sm:p-5 font-mono text-xs sm:text-sm text-[#e0e0e0] leading-relaxed overflow-x-auto">
        {children}
      </div>
    </div>
  );
};
