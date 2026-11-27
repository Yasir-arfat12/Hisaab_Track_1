import { Link } from 'react-router-dom';
import { AlertCircle, Inbox } from 'lucide-react';
import type { PromiseSummary, PromiseStatus } from '../../types';
import { AmountDisplay, DateDisplay, StatusBadge } from './DesignTokens';

export function PromiseListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div aria-label="Loading promises" className="space-y-3">
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          className="h-20 animate-pulse rounded-xl border border-slate-200 bg-white p-4"
        />
      ))}
    </div>
  );
}

export function PromiseList({
  items,
  isLoading,
  errorMessage,
  onRetry,
  hasActiveFilters,
  onClearFilters,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
}: {
  items: PromiseSummary[];
  isLoading: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
  hasActiveFilters?: boolean;
  onClearFilters?: () => void;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  onLoadMore?: () => void;
}) {
  if (isLoading) {
    return <PromiseListSkeleton />;
  }

  if (errorMessage) {
    return (
      <div
        role="alert"
        className="flex flex-col items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center"
      >
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Inbox className="mx-auto h-8 w-8 text-slate-400" />
        <h3 className="mt-3 text-sm font-semibold text-slate-900">
          {hasActiveFilters ? 'No promises match your filters' : 'No promises tracked yet'}
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          {hasActiveFilters
            ? 'Try clearing or adjusting your active filters.'
            : 'Sync your Gmail or trigger a scenario in the Demo Simulator to get started.'}
        </p>
        <div className="mt-4 flex justify-center gap-3">
          {hasActiveFilters && onClearFilters ? (
            <button
              type="button"
              onClick={onClearFilters}
              className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700"
            >
              Clear filters
            </button>
          ) : (
            <Link
              to="/demo"
              className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700"
            >
              Open Demo Simulator
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Mobile-first stacked cards */}
      <div className="space-y-3 md:hidden">
        {items.map((item) => (
          <Link
            key={item.promise_id}
            to={`/promises/${item.promise_id}`}
            className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-brand-300"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">{item.merchant_name}</p>
                <p className="mt-0.5 text-xs capitalize text-slate-500">
                  {(item.category ?? 'other').replace('_', ' ')}
                </p>
              </div>
              <StatusBadge status={item.status as PromiseStatus} />
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
              <AmountDisplay
                paise={item.amount_paise}
                className="text-base font-bold text-slate-900"
              />
              <span>
                Due: <DateDisplay iso={item.due_date} />
              </span>
            </div>
          </Link>
        ))}
      </div>

      {/* Desktop table */}
      <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm md:block">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Merchant</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Due Date</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.promise_id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">
                  <Link
                    to={`/promises/${item.promise_id}`}
                    className="text-brand-700 hover:underline"
                  >
                    {item.merchant_name}
                  </Link>
                </td>
                <td className="px-4 py-3 capitalize text-slate-600">
                  {(item.category ?? 'other').replace('_', ' ')}
                </td>
                <td className="px-4 py-3 font-semibold text-slate-900">
                  <AmountDisplay paise={item.amount_paise} />
                </td>
                <td className="px-4 py-3 text-slate-600">
                  <DateDisplay iso={item.due_date} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={item.status as PromiseStatus} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasNextPage && onLoadMore && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={onLoadMore}
            disabled={isFetchingNextPage}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {isFetchingNextPage ? 'Loading more...' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  );
}
