// API Type Definitions

// Transaction Types
export interface Transaction {
  transaction_id: string;
  status: string;
  amount: number;
  currency: string;
  originator_country: string;
  beneficiary_country: string;
  created_at: string;
  processing_completed_at: string | null;
}

export interface TransactionStatus {
  transaction_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicableRule {
  rule_id: string;
  title: string;
  description: string;
  source: string;
  rule_type: string;
  jurisdiction: string;
  severity: string;
  score: number;
  metadata: Record<string, any>;
}

export interface BayesianPosterior {
  risk_value: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface ComplianceReport {
  transaction_id: string;
  risk_band: "low" | "medium" | "high" | "critical";
  risk_score: number;
  rules_evaluated: number;
  rules_violated: number;
  applicable_rules: ApplicableRule[];
  patterns_detected: any[];
  bayesian_posterior: BayesianPosterior;
  compliance_summary: string;
  recommendations: any[];
  alerts_generated: any[];
  remediation_actions: any[];
  processed_at: string;
  processing_time_seconds: number;
}

export interface TransactionDetail extends TransactionStatus {
  compliance?: ComplianceReport;
}

// Document Types
export interface UploadedDocument {
  document_id: string;
  filename: string;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_score: number;
  processing_completed_at: string;
  report_text?: string;
}

// Rule Types
export type RuleType = "internal" | "external";
export type Regulator = "HKMA" | "MAS" | "FINMA";
export type Jurisdiction = "HK" | "SG" | "CH";

export interface RuleItem {
  rule_id: string;
  rule_type: RuleType;
  title: string;
  description?: string | null;
  text: string;
  section?: string | null; // internal only
  regulator?: Regulator | null; // external only
  jurisdiction?: Jurisdiction | null;
  source?: string | null;
  effective_date?: string | null;
  version?: string | null;
  is_active: boolean;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface RulesResponse {
  total: number;
  internal_count?: number;
  external_count?: number;
  rules: RuleItem[];
  page: number;
  page_size: number;
  filters_applied?: Record<string, any>;
}

export interface RulesFilters {
  search?: string;
  rule_type?: RuleType | "all";
  regulator?: Regulator;
  jurisdiction?: Jurisdiction;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

// Internal Rules Upload Types
export interface InternalRuleInput {
  rule_id?: string; // Optional - if provided, will update existing rule
  text: string;
  section?: string;
  obligation_type?: string;
  conditions?: string[];
  expected_evidence?: string[];
  penalty_level?: string;
  effective_date: string; // Required field
  sunset_date?: string;
  version?: string;
  source?: string;
  metadata?: Record<string, any>;
}

export interface InternalRulesPayload {
  rules: InternalRuleInput[];
}

export interface InternalRulesUploadResponse {
  message: string;
  filename?: string;
  total_rules?: number;
  created?: number;
  updated?: number;
  skipped?: number;
  errors?: any;
}
