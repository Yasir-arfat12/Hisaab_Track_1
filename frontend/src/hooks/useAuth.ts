import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import type { UserProfile } from '../types';

export function useAuthMe() {
  return useQuery<UserProfile, ApiError>({
    queryKey: queryKeys.authMe(),
    queryFn: () => apiFetch<UserProfile>('/api/v1/auth/me'),
    retry: false,
    staleTime: 60_000,
  });
}

export function useDemoLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{
        user_id: string;
        email: string;
        display_name: string;
        is_demo: boolean;
        seed_scenario: string;
      }>('/api/v1/auth/demo', { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.authMe() });
    },
  });
}

export function useGoogleStart() {
  return useMutation({
    mutationFn: () => apiFetch<{ redirect_url: string }>('/api/v1/auth/google/start'),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ logged_out: boolean }>('/api/v1/auth/logout', { method: 'POST' }),
    onSuccess: () => {
      queryClient.setQueryData(queryKeys.authMe(), null);
      queryClient.removeQueries({ queryKey: queryKeys.authMe() });
    },
  });
}
