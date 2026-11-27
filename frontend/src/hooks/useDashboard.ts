import { useQuery } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import type { DashboardSummary } from '../types';

export function useDashboard() {
  return useQuery<DashboardSummary, ApiError>({
    queryKey: queryKeys.dashboard(),
    queryFn: () => apiFetch<DashboardSummary>('/api/v1/dashboard/summary'),
  });
}
