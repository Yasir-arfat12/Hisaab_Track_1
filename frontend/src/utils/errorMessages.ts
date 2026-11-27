const ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: 'Please sign in to continue.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  NOT_FOUND: 'The requested item could not be found.',
  RATE_LIMITED: 'Too many requests. Please wait a moment and try again.',
  LLM_UNAVAILABLE: 'AI extraction is temporarily unavailable. Please retry.',
  GMAIL_AUTH_EXPIRED: 'Gmail access has expired. Please reconnect your account.',
  SYNC_IN_PROGRESS: 'A Gmail sync is already running — please wait.',
  PROMISE_NOT_FOUND: 'Promise not found.',
  CREDIT_UPLOAD_FAILED:
    'CSV upload failed. Ensure required columns exist: date, description, amount, reference_number.',
  JOB_NOT_FOUND: 'Background job not found.',
  DOSSIER_GENERATION_FAILED: 'Evidence dossier PDF is not ready yet. Please generate it first.',
};

export function mapErrorMessage(code?: string | null, fallback?: string): string {
  if (code && code in ERROR_MESSAGES) {
    return ERROR_MESSAGES[code];
  }
  return fallback || 'Something went wrong. Please try again.';
}
