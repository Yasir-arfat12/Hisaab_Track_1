import type { PromiseStatus } from '../../types/domain';
import { formatIstDate, formatPaiseToInr } from '../../utils/formatters';

const STATUS_STYLES: Record<PromiseStatus, { label: string; classes: string }> = {
  pending: {
    label: 'Pending',
    classes: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  },
  kept: {
    label: 'Kept',
    classes: 'bg-green-100 text-green-800 border-green-300',
  },
  overdue: {
    label: 'Overdue',
    classes: 'bg-red-100 text-red-800 border-red-300',
  },
  needs_review: {
    label: 'Needs Review',
    classes: 'bg-amber-100 text-amber-900 border-amber-300',
  },
  dismissed: {
    label: 'Dismissed',
    classes: 'bg-gray-100 text-gray-700 border-gray-300',
  },
};

export function StatusBadge({ status }: { status: PromiseStatus }) {
  const cfg = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.classes}`}
    >
      {cfg.label}
    </span>
  );
}

export function AmountDisplay({
  paise,
  fallback = '—',
  className = '',
}: {
  paise: number | null | undefined;
  fallback?: string;
  className?: string;
}) {
  return <span className={`font-mono tabular-nums ${className}`}>{formatPaiseToInr(paise, fallback)}</span>;
}

export function DateDisplay({
  iso,
  format = 'date',
  className = '',
}: {
  iso: string | null | undefined;
  format?: 'date' | 'datetime';
  className?: string;
}) {
  return <span className={className}>{formatIstDate(iso, format)}</span>;
}

export function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const barColor = pct < 50 ? 'bg-red-500' : pct <= 75 ? 'bg-amber-500' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2" title={`LLM confidence: ${pct}%`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{pct}%</span>
    </div>
  );
}

const RUNG_LABELS: Record<number, { label: string; classes: string }> = {
  1: { label: 'Rung 1 · Polite Nudge', classes: 'bg-yellow-100 text-yellow-800' },
  2: { label: 'Rung 2 · Formal Grievance', classes: 'bg-orange-100 text-orange-800' },
  3: { label: 'Rung 3 · NCH / Ombudsman', classes: 'bg-red-100 text-red-800' },
  4: { label: 'Rung 4 · Consumer Commission', classes: 'bg-rose-200 text-rose-950' },
};

export function EscalationRungBadge({ rung }: { rung: number }) {
  const cfg = RUNG_LABELS[rung] ?? RUNG_LABELS[1];
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}
