import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, AlertTriangle } from 'lucide-react';
import type { PromiseFilterParams } from '../api/queryKeys';
import { AmountDisplay } from '../components/domain/DesignTokens';
import { GmailSyncBanner } from '../components/domain/GmailSyncBanner';
import { PromiseFilters } from '../components/domain/PromiseFilters';
import { PromiseList } from '../components/domain/PromiseList';
import { PageHeader } from '../components/layout/AppShell';
import { useDashboard } from '../hooks/useDashboard';
import { usePromises } from '../hooks/usePromises';

export function DashboardPage() {
  const [filters, setFilters] = useState<PromiseFilterParams>({});
  const dashboard = useDashboard();
  const promises = usePromises(filters);

  const items = promises.data?.pages.flatMap((p) => p.items) ?? [];
  const hasActiveFilters = Boolean(
    filters.status || filters.category || filters.date_from || filters.date_to,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Track what companies owe you and verify every rupee."
        actions={
          <Link
            to="/promises"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            View all promises
          </Link>
        }
      />

      <GmailSyncBanner />

      {/* Owed to You summary */}
      {dashboard.isLoading ? (
        <div aria-label="Loading summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="h-28 animate-pulse rounded-xl border border-slate-200 bg-white" />
          ))}
        </div>
      ) : dashboard.isError ? (
        <div
          role="alert"
          className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{dashboard.error.userMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => dashboard.refetch()}
            className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      ) : dashboard.data ? (
        <>
          <section
            aria-label="Owed to You summary"
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            <div className="rounded-xl border border-brand-200 bg-brand-50 p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                Owed to You
              </p>
              <AmountDisplay
                paise={dashboard.data.total_owed_paise}
                className="mt-2 block text-2xl font-extrabold text-brand-900"
              />
              <p className="mt-1 text-xs text-brand-700">
                Across {dashboard.data.counts.pending + dashboard.data.counts.overdue + dashboard.data.counts.needs_review} open promises
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Overdue</p>
              <AmountDisplay
                paise={dashboard.data.total_overdue_paise}
                className="mt-2 block text-2xl font-bold text-slate-900"
              />
              <p className="mt-1 text-xs text-slate-500">
                {dashboard.data.counts.overdue} overdue promises
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-green-700">Kept</p>
              <AmountDisplay
                paise={dashboard.data.total_kept_paise}
                className="mt-2 block text-2xl font-bold text-slate-900"
              />
              <p className="mt-1 text-xs text-slate-500">
                {dashboard.data.counts.kept} verified credits
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                Needs Review
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {dashboard.data.counts.needs_review}
              </p>
              <button
                type="button"
                onClick={() => setFilters({ status: 'needs_review' })}
                className="mt-1 text-xs font-medium text-brand-600 hover:underline"
              >
                Review flagged →
              </button>
            </div>
          </section>

          {dashboard.data.counts.overdue > 0 && (
            <div className="flex flex-col justify-between gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>
                  You have <strong>{dashboard.data.counts.overdue}</strong> overdue promise(s) ready
                  for escalation.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setFilters({ status: 'overdue' })}
                className="self-start text-xs font-semibold text-red-700 underline sm:self-auto"
              >
                Show overdue
              </button>
            </div>
          )}
        </>
      ) : null}

      <PromiseFilters
        filters={filters}
        onChange={setFilters}
        onClear={() => setFilters({})}
      />

      <PromiseList
        items={items}
        isLoading={promises.isLoading}
        errorMessage={promises.error?.userMessage ?? null}
        onRetry={() => promises.refetch()}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={() => setFilters({})}
        hasNextPage={promises.hasNextPage}
        isFetchingNextPage={promises.isFetchingNextPage}
        onLoadMore={() => promises.fetchNextPage()}
      />
    </div>
  );
}
