import { useInfiniteQuery } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys, type PromiseFilterParams } from '../api/queryKeys';
import type { PromiseSummary } from '../types';

export interface PromiseListResponse {
  items: PromiseSummary[];
  next_cursor: string | null;
  prev_cursor: string | null;
  limit: number;
}

export function usePromises(filters: PromiseFilterParams = {}, limit = 20) {
  return useInfiniteQuery<PromiseListResponse, ApiError>({
    queryKey: queryKeys.promises(filters),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      if (filters.status) params.set('status', filters.status);
      if (filters.category) params.set('category', filters.category);
      if (filters.merchant_id) params.set('merchant_id', filters.merchant_id);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);
      if (pageParam) params.set('cursor', String(pageParam));
      return apiFetch<PromiseListResponse>(`/api/v1/promises?${params.toString()}`);
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}
