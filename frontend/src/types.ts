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
