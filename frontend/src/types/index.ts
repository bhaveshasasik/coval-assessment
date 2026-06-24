// Type definitions for API responses

export interface WorkflowNode {
  id: string;
  type: 'start' | 'decision' | 'process' | 'end';
  data: {
    label: string;
    description: string;
  };
  position: {
    x: number;
    y: number;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

export interface Workflow {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface TranscriptTurn {
  role: 'user' | 'assistant';
  content: string;
  beginning: number;
  end: number;
}

export interface Transcript {
  turns: TranscriptTurn[];
}

export interface NodeResult {
  node_id: string;
  satisfied: boolean;
  violations: Array<{
    code: string;
    severity: string;
    description: string;
    node_id?: string;
    edge?: string;
    timestamp?: number;
  }>;
  requires_human_review: boolean;
  verified_timestamp?: number;
}

export interface VerificationResult {
  id: string;
  workflow_name?: string;
  verdict: 'PASS' | 'FAIL';
  violations: Array<{
    code: string;
    severity: string;
    description: string;
    node_id?: string;
    edge?: string;
    timestamp?: number;
  }>;
  metrics: {
    node_completion_rate: number;
    critical_node_pass: boolean;
    edge_accuracy: number;
    valid_path_matched: boolean;
    order_violation: boolean;
    first_deviation_point?: number;
    low_confidence_count: number;
    unauthorized_steps: number;
    sub_requirement_coverage?: number;
  };
  actual_sequence: string[];
  required_sequence: string[];
  requires_human_review: boolean;
  node_verdicts: NodeResult[];
  summary: string;
}

export interface VerificationRequest {
  workflow: Workflow;
  transcript: Transcript;
  workflow_name?: string;
  confidence_threshold?: number;
}

export interface VerificationResponse {
  verification_id: string;
  result: VerificationResult;
  workflow?: Workflow;
  transcript?: Transcript;
}

export interface HistoryItem {
  id: string;
  workflow_name?: string;
  timestamp: string;
  verdict: 'PASS' | 'FAIL';
  node_completion_rate: number;
  edge_accuracy: number;
  critical_violation_count: number;
  requires_human_review: boolean;
}

export interface DatabaseVerification {
  id: string;
  workflow_name?: string;
  timestamp: string;
  verdict: 'PASS' | 'FAIL';
  workflow: Workflow;
  transcript: Transcript;
  results: VerificationResult;
}

export interface MetricsExport {
  conversation_id: string;
  workflow_id: string;
  verified_at: string;
  result: 'PASS' | 'FAIL';
  violations: Array<{
    code: string;
    severity: string;
    description: string;
    node_id?: string;
    edge?: string;
    timestamp?: number;
  }>;
  metrics: {
    node_completion_rate: number;
    critical_node_pass: boolean;
    edge_accuracy: number;
    valid_path_matched: boolean;
    order_violation: boolean;
    first_deviation_point?: number;
    sub_requirement_coverage?: number;
    low_confidence_count: number;
    unauthorized_steps: number;
  };
  steps_taken: string[];
  steps_required: string[];
  human_review_required: boolean;
  node_results: Array<{
    node_id: string;
    label: string;
    status: 'visited' | 'out_of_order' | 'not_visited';
    evidence_quote?: string | null;
    verified_at?: number | null;
  }>;
}
