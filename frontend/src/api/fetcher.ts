import type { ApiEnvelope, ApiErrorBody } from '../types/domain';
import { mapErrorMessage } from '../utils/errorMessages';

type ApiErrorListener = (error: ApiError) => void;
const listeners = new Set<ApiErrorListener>();

export function subscribeApiErrors(listener: ApiErrorListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notifyApiError(err: ApiError): void {
  listeners.forEach((fn) => fn(err));
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;
  readonly userMessage: string;

  constructor(error: ApiErrorBody, status: number) {
    const userMessage = mapErrorMessage(error.code, error.message);
    super(userMessage);
    this.name = 'ApiError';
    this.code = error.code;
    this.status = status;
    this.details = error.details ?? {};
    this.userMessage = userMessage;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? '';
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase();
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  const headers = new Headers(options.headers);
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCookie('csrf_token');
    if (csrf && !headers.has('X-CSRF-Token')) {
      headers.set('X-CSRF-Token', csrf);
    }
    if (method === 'POST' && !headers.has('Idempotency-Key') && typeof crypto !== 'undefined') {
      headers.set('Idempotency-Key', crypto.randomUUID());
    }
  }

  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}${path}`, {
    credentials: 'include',
    ...options,
    method,
    headers,
  });

  let envelope: ApiEnvelope<T>;
  try {
    envelope = (await res.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiError(
      { code: 'INTERNAL_ERROR', message: `Unexpected response (${res.status})` },
      res.status,
    );
  }

  if (!res.ok || envelope.error) {
    const err = new ApiError(
      envelope.error ?? { code: 'INTERNAL_ERROR', message: `Request failed (${res.status})` },
      res.status,
    );
    notifyApiError(err);
    throw err;
  }

  return envelope.data as T;
}
