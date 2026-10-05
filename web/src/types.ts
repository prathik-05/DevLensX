export interface RepoSummary {
  repository: string;
  language: string;
  framework: string;
  repo_type?: string;
  analysis_scope?: string;
  build_system?: string;
  has_java_capability?: boolean;
  language_profile?: Record<string, any>;
  controllers: number;
  services: number;
  repositories: number;
  entities: number;
  rest_apis: number;
  total_classes: number;
  total_injected_dependencies: number;
}

export interface SubScores {
  architecture: number;
  security: number;
  maintainability: number;
  coupling: number;
  evidence_coverage: number;
}

export interface IntelligenceScore {
  overall: number;
  sub_scores: SubScores;
  sub_score_explanations?: Record<string, string>;
  score_weights_configured?: Record<string, number>;
}

export interface EvidenceTrail {
  graph_check: { passed: boolean; details: string };
  ast_check: { passed: boolean; details: string };
  semgrep_check: { passed: boolean; details: string };
  structural_check: { passed: boolean; details: string };
}

export interface RecommendationCard {
  rank: number;
  title: string;
  target_component: string;
  file: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  reason: string;
  evidence_summary: string;
  affected_components: string[];
  estimated_effort: 'LOW' | 'MEDIUM' | 'HIGH';
  expected_benefit: string;
  evidence_coverage_score: number;
  evidence_trail: EvidenceTrail;
}

export interface TimingMetrics {
  parse_ast_ms: number;
  graph_build_ms: number;
  multi_agent_scan_ms: number;
  critic_grounding_verification_ms: number;
  recommendation_synthesis_ms: number;
  total_execution_ms: number;
}

export interface GraphNode {
  id: string;
  name: string;
  package: string;
  kind: string;
  stereotype: string;
  file: string;
  incoming_count: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AnalysisResponse {
  analysis_run_id?: string;
  repository: string;
  is_non_java_repo?: boolean;
  status_message?: string;
  repo_summary: RepoSummary;
  parse_stats: Record<string, any>;
  graph_edge_stats: Record<string, any>;
  timing_metrics: TimingMetrics;
  raw_findings_count: number;
  repository_intelligence_score?: IntelligenceScore | null;
  top_engineering_recommendations: RecommendationCard[];
  total_verified_findings: number;
  total_rejected_findings: number;
  rejected_findings_sample?: any[];
  knowledge_graph?: KnowledgeGraphData;
  classes?: any[];
}

export interface ChangeImpactResult {
  target_class: string;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  total_affected_count: number;
  affected_classes: Array<{ class_name: string; stereotype: string; file: string; is_test: boolean }>;
  affected_controllers: Array<{ class_name: string; stereotype: string }>;
  affected_services: Array<{ class_name: string; stereotype: string }>;
  affected_tests: Array<{ class_name: string }>;
  impact?: {
    directly_affected: number;
    potentially_affected: number;
    affected_names: string[];
  };
}

export interface HybridContext {
  query: string;
  graph_evidence_triples: Array<{ subject: string; predicate: string; object: string }>;
  relevant_ast_nodes: Array<{
    class_name: string;
    stereotype: string;
    file: string;
    snippet: string;
    relevance_score: number;
  }>;
}

export interface IntroductionResponse {
  narrative: string;
  repo_name: string;
  repo_type: string;
  health_status: 'Healthy' | 'Needs Attention' | 'Critical';
  core_modules: string[];
  most_connected_class: { name: string; dependent_count: number };
  top_concerns: Array<{ summary: string; severity: string; category: string; finding_ids: string[] }>;
  snapshot: {
    controllers: number;
    services: number;
    repositories: number;
    entities: number;
    rest_apis: number;
    total_classes: number;
  };
}

export interface PlannerClassifyResponse {
  intent: 'feature_planning' | 'architecture' | 'security' | 'debugging' | 'refactor' | 'documentation' | 'testing';
}

export interface CopilotAskResponse {
  plain_english: string;
  recommendation: string;
  impact: {
    directly_affected: number;
    potentially_affected: number;
    affected_names: string[];
  };
  evidence: {
    graph: boolean;
    ast: boolean;
    semgrep: boolean;
    structure: boolean;
    sources: string[];
  };
  follow_up_suggestions: string[];
  is_interpretation: boolean;
}

export interface RepoDocsResponse {
  readme: string;
  architecture_guide: string;
  onboarding_guide: string;
  folder_breakdown: string;
  deployment_guide: string;
}

export interface FileSummaryResponse {
  file_path: string;
  class_name: string;
  stereotype: string;
  purpose: string;
  used_by_count: number;
  dependencies: string[];
  related_files: string[];
  risks: string;
}

// D7 Verified Documentation Types
export interface VerifiedClaim {
  subject: string;
  predicate: string;
  object: string;
  claim_type: string;
  verdict: string;
  evidence_source?: string;
  line_reference?: string;
}

export interface DocSection {
  heading: string;
  content: string;
  verdict: string;
  claims: VerifiedClaim[];
  evidence_refs: Array<{
    repository_id: string;
    analysis_run_id: string;
    commit_hash?: string | null;
    file_path: string;
    line_start: number;
    line_end: number;
    symbol_name?: string | null;
    evidence_type?: string;
  }>;
  diagram_ids: string[];
}

export interface VerifiedDocPage {
  id: string;
  title: string;
  purpose: string;
  repository_id: string;
  analysis_run_id: string;
  commit_hash?: string | null;
  status: 'VERIFIED' | 'VERIFIED_WITH_SUGGESTIONS' | 'PARTIALLY_VERIFIED' | 'INSUFFICIENT_EVIDENCE' | 'GENERATION_FAILED';
  verification_summary: {
    verified: number;
    suggestions: number;
    insufficient_evidence: number;
  };
  sections: DocSection[];
  diagram_ids: string[];
  generated_at?: string;
}
