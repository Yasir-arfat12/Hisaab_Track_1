import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Check, ShieldAlert, X } from 'lucide-react';
import { apiFetch } from '../../api/fetcher';
import { queryKeys } from '../../api/queryKeys';
import { usePromises } from '../../hooks/usePromises';
import type { PromiseSummary, VerifyResult } from '../../types';
import { AmountDisplay, DateDisplay, StatusBadge } from './DesignTokens';

export function NeedsReviewQueue() {
  const queryClient = useQueryClient();
  const reviewQuery = usePromises({ status: 'needs_review' });
  const items = reviewQuery.data?.pages.flatMap((p) => p.items) ?? [];

  const confirmMutation = useMutation<VerifyResult, Error, string>({
    mutationFn: (promiseId) =>
      apiFetch<VerifyResult>(`/api/v1/verify/${promiseId}`, { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['promises'] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
    },
  });

  const dismissMutation = useMutation<PromiseSummary, Error, string>({
    mutationFn: (promiseId) =>
      apiFetch<PromiseSummary>(`/api/v1/promises/${promiseId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'dismissed' }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['promises'] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
    },
  });

  if (reviewQuery.isLoading || items.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Needs Review Queue"
      className="rounded-xl border border-amber-300 bg-amber-50 p-5 shadow-sm"
    >
      <div className="flex items-center gap-2 text-amber-900">
        <ShieldAlert className="h-5 w-5 shrink-0" />
        <h2 className="text-base font-semibold">Needs Review Queue ({items.length})</h2>
      </div>
      <p className="mt-1 text-xs text-amber-800">
        Ambiguous matches, partial refunds, and flagged extractions are never auto-closed. Confirm
        or dismiss each item below.
      </p>

      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div
            key={item.promise_id}
            className="flex flex-col justify-between gap-3 rounded-lg border border-amber-200 bg-white p-4 sm:flex-row sm:items-center"
          >
            <div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/promises/${item.promise_id}`}
                  className="text-sm font-semibold text-brand-700 hover:underline"
                >
                  {item.merchant_name}
                </Link>
                <StatusBadge status="needs_review" />
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-slate-600">
                <AmountDisplay paise={item.amount_paise} className="font-semibold text-slate-900" />
                <span>
                  Due: <DateDisplay iso={item.due_date} />
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => confirmMutation.mutate(item.promise_id)}
                disabled={confirmMutation.isPending || dismissMutation.isPending}
                className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" />
                Confirm Match
              </button>
              <button
                type="button"
                onClick={() => dismissMutation.mutate(item.promise_id)}
                disabled={confirmMutation.isPending || dismissMutation.isPending}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
