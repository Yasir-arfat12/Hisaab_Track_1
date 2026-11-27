import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { PromiseFilterParams } from '../api/queryKeys';
import { CsvUploadCard } from '../components/domain/CsvUploadCard';
import { GmailSyncBanner } from '../components/domain/GmailSyncBanner';
import { NeedsReviewQueue } from '../components/domain/NeedsReviewQueue';
import { PromiseFilters } from '../components/domain/PromiseFilters';
import { PromiseList } from '../components/domain/PromiseList';
import { PageHeader } from '../components/layout/AppShell';
import { usePromises } from '../hooks/usePromises';

export function PromisesPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<PromiseFilterParams>({
    status: searchParams.get('status') || undefined,
    category: searchParams.get('category') || undefined,
  });

  const promises = usePromises(filters);
  const items = promises.data?.pages.flatMap((p) => p.items) ?? [];
  const hasActiveFilters = Boolean(
    filters.status || filters.category || filters.date_from || filters.date_to,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Promises & Bank Proof"
        subtitle="Sync Gmail, upload bank statement CSVs, and review flagged items."
      />

      <GmailSyncBanner />
      <NeedsReviewQueue />
      <CsvUploadCard />

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
