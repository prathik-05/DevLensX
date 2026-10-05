import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useAppStore } from '../store';

interface ThemeToggleProps {
  className?: string;
  variant?: 'button' | 'compact' | 'switch';
  showLabel?: boolean;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  className = '',
  variant = 'button',
  showLabel = true,
}) => {
  const theme = useAppStore(s => s.theme);
  const toggleTheme = useAppStore(s => s.toggleTheme);
  const isDark = theme === 'dark';

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      toggleTheme();
    }
  };

  if (variant === 'switch') {
    return (
      <button
        type="button"
        role="switch"
        aria-checked={isDark}
        aria-label={`Toggle theme (currently ${theme})`}
        title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
        onClick={toggleTheme}
        onKeyDown={handleKeyDown}
        className={`relative inline-flex items-center h-6 w-12 rounded-full p-0.5 border transition-colors duration-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--dl-accent)] ${
          isDark
            ? 'bg-[#141519] border-zinc-700'
            : 'bg-[#f1f5f9] border-[#000000]'
        } ${className}`}
      >
        <span
          className={`pointer-events-none flex items-center justify-center w-4 h-4 rounded-full transition-transform duration-200 ease-out shadow-sm ${
            isDark
              ? 'translate-x-6 bg-zinc-200 text-black'
              : 'translate-x-0 bg-white text-zinc-700 border border-neutral-300'
          }`}
        >
          {isDark ? (
            <Moon className="w-2.5 h-2.5 fill-current" />
          ) : (
            <Sun className="w-2.5 h-2.5 fill-current" />
          )}
        </span>
      </button>
    );
  }

  // Default Clean Button
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={`Toggle theme (currently ${theme})`}
      title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
      onClick={toggleTheme}
      onKeyDown={handleKeyDown}
      className={`group relative flex items-center gap-2 text-[10px] font-mono font-bold uppercase px-2.5 py-1 transition-all duration-150 cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--dl-accent)] active:translate-x-[1px] active:translate-y-[1px] ${
        isDark
          ? 'bg-[#141519] border border-[#2a2b32] text-zinc-200 shadow-none hover:bg-[#1c1d23] hover:border-zinc-600'
          : 'bg-white border border-black text-[#0f172a] shadow-[2px_2px_0px_0px_#000000] hover:bg-neutral-50'
      } ${className}`}
    >
      <span className="relative flex items-center justify-center w-3.5 h-3.5">
        {isDark ? (
          <Moon className="w-3.5 h-3.5 text-zinc-200 transition-transform duration-200 group-hover:-rotate-12" />
        ) : (
          <Sun className="w-3.5 h-3.5 text-zinc-700 transition-transform duration-200 group-hover:rotate-45" />
        )}
      </span>
      {showLabel && (
        <span className="tracking-wider text-zinc-300 dark:text-zinc-300">
          {isDark ? 'DARK' : 'LIGHT'}
        </span>
      )}
    </button>
  );
};
