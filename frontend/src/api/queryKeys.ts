export interface PromiseFilterParams {
  status?: string;
  category?: string;
  merchant_id?: string;
  date_from?: string;
  date_to?: string;
}

export const queryKeys = {
  authMe: () => ['auth', 'me'] as const,
  dashboard: () => ['dashboard'] as const,
  promises: (filters: PromiseFilterParams = {}) => ['promises', filters] as const,
  promise: (id: string) => ['promises', id] as const,
  credits: (filters: Record<string, unknown> = {}) => ['credits', filters] as const,
  merchant: (id: string) => ['merchants', id] as const,
  job: (id: string) => ['jobs', id] as const,
  syncStatus: () => ['gmail', 'sync-status'] as const,
  escalationNext: (id: string) => ['escalation', id, 'next-step'] as const,
};
