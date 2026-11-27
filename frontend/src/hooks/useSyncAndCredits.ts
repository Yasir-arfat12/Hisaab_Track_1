import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import type { BankCredit } from '../types';

export interface GmailStatusData {
  connected: boolean;
  email: string | null;
  last_synced_at: string | null;
  sync_status: 'idle' | 'queued' | 'running';
  active_job_id: string | null;
  emails_processed: number;
}

export function useGmailStatus() {
  return useQuery<GmailStatusData, ApiError>({
    queryKey: queryKeys.syncStatus(),
    queryFn: () => apiFetch<GmailStatusData>('/api/v1/gmail/status'),
  });
}

export function useGmailConnect() {
  return useMutation<{ redirect_url: string }, ApiError>({
    mutationFn: () =>
      apiFetch<{ redirect_url: string }>('/api/v1/gmail/connect', { method: 'POST' }),
  });
}

export function useGmailSync() {
  const queryClient = useQueryClient();
  return useMutation<{ job_id: string; status: string; enqueued_at: string }, ApiError>({
    mutationFn: () =>
      apiFetch<{ job_id: string; status: string; enqueued_at: string }>('/api/v1/gmail/sync', {
        method: 'POST',
        body: JSON.stringify({ full_resync: false }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.syncStatus() });
    },
  });
}

export function useCredits() {
  return useQuery<{ items: BankCredit[]; next_cursor: string | null; limit: number }, ApiError>({
    queryKey: queryKeys.credits(),
    queryFn: () =>
      apiFetch<{ items: BankCredit[]; next_cursor: string | null; limit: number }>(
        '/api/v1/credits',
      ),
  });
}

export function useUploadCredits() {
  const queryClient = useQueryClient();
  return useMutation<
    { job_id: string; rows_detected: number; status: string },
    ApiError,
    { file: File; bank_name: string; account_last4?: string }
  >({
    mutationFn: ({ file, bank_name, account_last4 }) => {
      const form = new FormData();
      form.append('file', file);
      form.append('bank_name', bank_name);
      if (account_last4) {
        form.append('account_last4', account_last4);
      }
      return apiFetch<{ job_id: string; rows_detected: number; status: string }>(
        '/api/v1/credits/upload',
        {
          method: 'POST',
          body: form,
        },
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.credits() });
    },
  });
}
