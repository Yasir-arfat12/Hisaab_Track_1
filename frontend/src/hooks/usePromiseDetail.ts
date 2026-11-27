import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import type {
  EscalationDraft,
  EscalationNextStep,
  Job,
  PromiseDetail,
  PromiseSummary,
  VerifyResult,
} from '../types';

export function usePromiseDetail(id: string) {
  return useQuery<PromiseDetail, ApiError>({
    queryKey: queryKeys.promise(id),
    queryFn: () => apiFetch<PromiseDetail>(`/api/v1/promises/${id}`),
    enabled: Boolean(id),
  });
}

export function usePatchPromise(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { status?: 'dismissed'; user_note?: string }) =>
      apiFetch<PromiseSummary>(`/api/v1/promises/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.promise(id) });
      await queryClient.invalidateQueries({ queryKey: ['promises'] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
    },
  });
}

export function useVerifyPromise(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<VerifyResult>(`/api/v1/verify/${id}`, {
        method: 'POST',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.promise(id) });
      await queryClient.invalidateQueries({ queryKey: ['promises'] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
    },
  });
}

export function useEscalationNextStep(id: string) {
  return useQuery<EscalationNextStep, ApiError>({
    queryKey: queryKeys.escalationNext(id),
    queryFn: () => apiFetch<EscalationNextStep>(`/api/v1/escalation/${id}/next-step`),
    enabled: Boolean(id),
  });
}

export function useGenerateEscalationDraft(id: string) {
  return useMutation({
    mutationFn: (body: {
      rung: number;
      tone: 'firm' | 'polite';
      include_legal_references: boolean;
    }) =>
      apiFetch<EscalationDraft>(`/api/v1/escalation/${id}/draft`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  });
}

export function useGenerateDossier(id: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ job_id: string; status: string; enqueued_at: string }>(
        `/api/v1/dossier/${id}/generate`,
        { method: 'POST' },
      ),
  });
}

export function useJobStatus(jobId: string | null) {
  return useQuery<Job, ApiError>({
    queryKey: queryKeys.job(jobId ?? ''),
    queryFn: () => apiFetch<Job>(`/api/v1/jobs/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const st = query.state.data?.status;
      if (st === 'completed' || st === 'failed') return false;
      return 1500;
    },
  });
}
