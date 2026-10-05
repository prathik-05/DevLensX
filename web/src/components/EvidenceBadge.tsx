import React from 'react';
import { VERDICT_META, type Verdict } from '../evidence';

interface EvidenceBadgeProps {
  verdict: Verdict;
  title?: string;
  compact?: boolean;
}

/**
 * D5 EvidenceBadge — canonical evidence verdict badge.
 * Exactly four states, no confidence percentages:
 *   🟢 VERIFIED · 🔵 AI SUGGESTION · 🔴 INSUFFICIENT EVIDENCE · ⚪ NOT VERIFIED
 */
export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({ verdict, title, compact }) => {
  const meta = VERDICT_META[verdict] ?? VERDICT_META.NOT_VERIFIED;
  return (
    <span
      title={title || meta.label}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wide ${meta.cls}`}
    >
      <span aria-hidden>{meta.emoji}</span>
      {!compact && <span>{meta.label}</span>}
    </span>
  );
};