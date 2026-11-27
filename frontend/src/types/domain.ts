export type PromiseStatus = 'pending' | 'kept' | 'overdue' | 'needs_review' | 'dismissed';

export type PromiseCategory = 'refund' | 'delivery_credit' | 'insurance' | 'ticket' | 'other';

export type ExtractionMethod = 'llm' | 'deterministic';

export type DemoScenario =
  | 'refund_arrives'
  | 'refund_delayed'
  | 'fake_promise'
  | 'duplicate_charge';

export type ApiErrorCode =
  | 'AUTH_REQUIRED'
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'RATE_LIMITED'
  | 'LLM_UNAVAILABLE'
  | 'GMAIL_AUTH_EXPIRED'
  | 'SYNC_IN_PROGRESS'
  | 'PROMISE_NOT_FOUND'
  | 'CREDIT_UPLOAD_FAILED'
  | 'JOB_NOT_FOUND'
  | 'DOSSIER_GENERATION_FAILED';

export interface ApiErrorBody {
  code: ApiErrorCode | string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiEnvelope<T> {
  data: T | null;
  error: ApiErrorBody | null;
}
