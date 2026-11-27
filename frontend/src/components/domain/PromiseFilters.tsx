import type { PromiseFilterParams } from '../../api/queryKeys';

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'kept', label: 'Kept' },
  { value: 'dismissed', label: 'Dismissed' },
];

const CATEGORY_OPTIONS = [
  { value: '', label: 'All categories' },
  { value: 'refund', label: 'Refund' },
  { value: 'delivery_credit', label: 'Delivery Credit' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'ticket', label: 'Ticket' },
  { value: 'other', label: 'Other' },
];

export function PromiseFilters({
  filters,
  onChange,
  onClear,
}: {
  filters: PromiseFilterParams;
  onChange: (next: PromiseFilterParams) => void;
  onClear: () => void;
}) {
  const hasFilters = Boolean(
    filters.status || filters.category || filters.date_from || filters.date_to,
  );

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Mobile-first horizontally scrollable status chips */}
      <div
        role="group"
        aria-label="Filter by status"
        className="flex items-center gap-2 overflow-x-auto pb-1"
      >
        {STATUS_OPTIONS.map((opt) => {
          const active = (filters.status ?? '') === opt.value;
          return (
            <button
              key={opt.label}
              type="button"
              onClick={() => onChange({ ...filters, status: opt.value || undefined })}
              aria-pressed={active}
              className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                active
                  ? 'border-brand-600 bg-brand-600 text-white'
                  : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="block text-xs font-medium text-slate-600">
          Category
          <select
            value={filters.category ?? ''}
            onChange={(e) => onChange({ ...filters, category: e.target.value || undefined })}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.label} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs font-medium text-slate-600">
          Due from
          <input
            type="date"
            value={filters.date_from ?? ''}
            onChange={(e) => onChange({ ...filters, date_from: e.target.value || undefined })}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          />
        </label>

        <label className="block text-xs font-medium text-slate-600">
          Due to
          <input
            type="date"
            value={filters.date_to ?? ''}
            onChange={(e) => onChange({ ...filters, date_to: e.target.value || undefined })}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          />
        </label>
      </div>

      {hasFilters && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClear}
            className="text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
