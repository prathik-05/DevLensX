// DevLensX Evidence Types (D5) — mirrors devlensx/evidence/models.py

export type EvidenceType = 'AST' | 'GRAPH' | 'CONFIG' | 'GIT' | 'VECTOR';

export type ResolutionStatus =
  | 'RESOLVED'
  | 'UNKNOWN_SNAPSHOT'
  | 'STALE_COMMIT'
  | 'FILE_NOT_FOUND'
  | 'PATH_VIOLATION'
  | 'BINARY_FILE'
  | 'FILE_TOO_LARGE'
  | 'INVALID_RANGE';

export interface EvidenceRef {
  repository_id: string;
  analysis_run_id: string;
  file_path: string;
  line_start: number;
  line_end: number;
  commit_hash?: string | null;
  symbol_id?: string | null;
  symbol_name?: string | null;
  evidence_type?: EvidenceType;
}

export interface SourceLine {
  n: number;
  content: string;
  in_range: boolean;
}

export interface ResolvedEvidence {
  status: ResolutionStatus;
  resolved: boolean;
  message: string;
  ref: EvidenceRef & { citation: string };
  lines?: SourceLine[];
  total_lines?: number;
  file_language?: string;
}

/** Verdict badges used across wiki/chat/diagrams (D5/D8 shared contract). */
export type Verdict = 'VERIFIED' | 'AI_SUGGESTION' | 'INSUFFICIENT_EVIDENCE' | 'NOT_VERIFIED';

export const VERDICT_META: Record<Verdict, { emoji: string; label: string; cls: string }> = {
  VERIFIED: { emoji: '🟢', label: 'VERIFIED', cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  AI_SUGGESTION: { emoji: '🔵', label: 'AI SUGGESTION', cls: 'text-sky-400 bg-sky-500/10 border-sky-500/30' },
  INSUFFICIENT_EVIDENCE: { emoji: '🔴', label: 'INSUFFICIENT EVIDENCE', cls: 'text-rose-400 bg-rose-500/10 border-rose-500/30' },
  NOT_VERIFIED: { emoji: '⚪', label: 'NOT VERIFIED', cls: 'text-slate-300 bg-slate-500/10 border-slate-500/30' },
};