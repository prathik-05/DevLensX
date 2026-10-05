// DevLensX Diagram Types (D6) — mirrors devlensx/diagrams/models.py
import type { EvidenceRef } from './evidence';

export type DiagramType =
  | 'DEPENDENCY'
  | 'ARCHITECTURE'
  | 'COMPONENT'
  | 'CALL_GRAPH'
  | 'DATA_FLOW'
  | 'SEQUENCE';

export type DiagramVerdict = 'VERIFIED' | 'AI_SUGGESTION' | 'INSUFFICIENT_EVIDENCE';

export interface DiagramNode {
  id: string;
  label: string;
  kind: string;
  verdict: DiagramVerdict;
  evidence_refs: EvidenceRef[];
  metadata?: Record<string, any>;
}

export interface DiagramEdge {
  source: string;
  target: string;
  relationship: string;
  verdict: DiagramVerdict;
  evidence_refs: EvidenceRef[];
  metadata?: Record<string, any>;
}

export interface DiagramValidation {
  valid: boolean;
  total_nodes: number;
  verified_nodes: number;
  inferred_nodes: number;
  unresolved_node_evidence: number;
  total_edges: number;
  verified_edges: number;
  inferred_edges: number;
  unresolved_edge_evidence: number;
}

export interface Diagram {
  id: string;
  type: DiagramType;
  title: string;
  repository_id: string;
  analysis_run_id: string;
  commit_hash?: string | null;
  generated_at?: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  validation?: DiagramValidation;
  mermaid_source: string;
  description?: string;
  verdict?: string;
}

export interface DiagramCatalogItem {
  id: string;
  type: DiagramType;
  title: string;
  node_count: number;
  edge_count: number;
  verdict: string;
  description: string;
}

export interface DiagramCatalogResponse {
  status: string;
  analysis_run_id: string;
  count: number;
  diagrams: DiagramCatalogItem[];
}
