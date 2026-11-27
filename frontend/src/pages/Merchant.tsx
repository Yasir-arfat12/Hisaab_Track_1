import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import { PromiseList } from '../components/domain/PromiseList';
import { PageHeader } from '../components/layout/AppShell';
import { usePromises } from '../hooks/usePromises';
import type { MerchantRecord } from '../types';

export function MerchantPage() {
  const { id = '' } = useParams<{ id: string }>();
  const record = useQuery<MerchantRecord, ApiError>({
    queryKey: queryKeys.merchant(id),
    queryFn: () => apiFetch<MerchantRecord>(`/api/v1/merchants/${id}/record`),
    enabled: Boolean(id),
  });
  const history = usePromises({ merchant_id: id });
  const historyItems = history.data?.pages.flatMap((p) => p.items) ?? [];

  if (record.isLoading) {
    return <div aria-label="Loading merchant record" className="h-32 animate-pulse rounded-xl bg-white" />;
  }
  if (record.isError || !record.data) {
    return (
      <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        {record.error?.userMessage ?? 'Merchant not found.'}
      </div>
    );
  }

  const m = record.data;
  return (
    <div className="space-y-6">
      <PageHeader
        title={m.merchant_name}
        subtitle="Promise-keeping record computed from your own tracked promises."
        actions={
          <Link
            to="/promises"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Back to Promises
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Total Promises</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{m.total_promises}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Kept</p>
          <p className="mt-1 text-2xl font-bold text-green-700">{m.kept_count}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Overdue</p>
          <p className="mt-1 text-2xl font-bold text-red-600">{m.overdue_count}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Keep Rate</p>
          <p className="mt-1 text-2xl font-bold text-brand-700">{m.keep_rate_pct}%</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Avg Resolution</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {m.average_resolution_days !== null && m.average_resolution_days !== undefined
              ? `${m.average_resolution_days}d`
              : '—'}
          </p>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Promise History</h2>
        <PromiseList
          items={historyItems}
          isLoading={history.isLoading}
          errorMessage={history.error?.userMessage ?? null}
          onRetry={() => history.refetch()}
        />
      </section>
    </div>
  );
}
