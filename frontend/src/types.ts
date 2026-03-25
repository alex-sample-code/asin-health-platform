export interface AsinScore {
  asin: string;
  seller_id: string;
  marketplace_id: string;
  lifecycle: string;
  sub_category: string;
  date: string;
  sales_score: number;
  inventory_score: number;
  advertising_score: number;
  after_sales_score: number;
  profitability_score: number;
  listing_score: number;
  weighted_score: number;
  final_score: number;
  trend_adjusted_score: number;
  health_label: HealthLabel;
  veto_applied: string | null;
  dimension_scores: Record<string, number>;
}

export type HealthLabel = 'healthy' | 'warning' | 'abnormal' | 'danger';
export type Lifecycle = 'new' | 'growth' | 'mature' | 'decline';

export interface ScoreListResponse {
  total: number;
  scores: AsinScore[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// ── 智能诊断 ──────────────────────────────────────────────────────────────

export interface ProblemDimension {
  dimension: string;
  dimension_cn: string;
  score: number;
  severity: 'critical' | 'warning' | 'attention';
  description: string;
}

export interface RootCause {
  hypothesis: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: string[];
}

export interface ActionItem {
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  title: string;
  steps: string[];
  expected_effect: string;
  timeline: string;
}

export interface BenchmarkComparison {
  category_position: string;
  weak_vs_benchmark: string[];
  competitor_insights: string;
}

export interface DiagnosisResponse {
  asin: string;
  health_label: HealthLabel;
  final_score: number;
  summary: string;
  problem_dimensions: ProblemDimension[];
  root_causes: RootCause[];
  action_plan: ActionItem[];
  benchmark: BenchmarkComparison;
}
