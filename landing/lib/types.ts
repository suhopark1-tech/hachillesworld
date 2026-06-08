export interface HasDataPoint {
  timestamp: string;
  has_score: number;
  level: string;
}

export interface HasTimeseriesResponse {
  agent_id: string;
  data_points: HasDataPoint[];
  from_ts: string | null;
  to_ts: string | null;
}

export interface MetricScore {
  name: string;
  value: number;
  threshold: number;
  unit: string;
  status: 'ok' | 'warning' | 'critical';
  description: string;
}

export interface CategoryScore {
  name: string;
  score: number;
  metrics: MetricScore[];
}

export interface ScanResponse {
  agent_name: string;
  level: string;
  level_label: string;
  laws_domain: string;
  composite_score: number;
  world_model_quality: CategoryScore;
  agency_level: CategoryScore;
  operational_health: CategoryScore;
  recommendations: string[];
  metadata: Record<string, unknown>;
}

export interface HarnessRule {
  rule_id: string;
  condition: string;
  action: string;
  severity: 'hard' | 'soft';
  source: string;
}

export interface HarnessPendingResponse {
  agent_id: string;
  rules: HarnessRule[];
}

export interface DriftAlert {
  agent_name: string;
  drift_value: number;
  threshold: number;
  recent_rate: number;
  recommended_action: string;
}

export interface AgentSummary {
  agent_id: string;
  name: string;
  domain: string;
  has_score: number | null;
  level: string | null;
  is_critical: boolean;
}

export interface AlertSettings {
  slack_webhook: string;
  email: string;
  has_warning_threshold: number;
  has_critical_threshold: number;
  drift_threshold: number;
}

export interface ConsentRecord {
  version: string;
  required: boolean;
  anonymous_benchmark: boolean;
  product_improvement: boolean;
  marketing_contact: boolean;
  public_case_study: boolean;
  consented_at: string;
  region: 'KR' | 'EU' | 'US' | 'JP';
}

export const CONSENT_STORAGE_KEY = 'haw_consent_v1';

export interface AccountRecord {
  email: string;
  company: string;
  region: 'KR' | 'EU' | 'US' | 'JP';
  created_at: string;
}

export interface OnboardingAgent {
  agent_id: string;
  name: string;
  domain: string;
  purpose: string;
  created_at: string;
}

export const ACCOUNT_STORAGE_KEY = 'haw_account_v1';
export const AGENTS_STORAGE_KEY  = 'haw_agents_v1';
