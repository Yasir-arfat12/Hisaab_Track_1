import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { getApiBaseUrl } from '../api/fetcher';
import {
  AmountDisplay,
  ConfidenceMeter,
  DateDisplay,
  EscalationRungBadge,
  StatusBadge,
} from '../components/domain/DesignTokens';
import { EscalationLadder } from '../components/domain/EscalationLadder';
import { PageHeader } from '../components/layout/AppShell';
import {
  useGenerateDossier,
  useJobStatus,
  usePatchPromise,
  usePromiseDetail,
  useVerifyPromise,
} from '../hooks/usePromiseDetail';
import type { PromiseStatus } from '../types';

export function PromiseDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const detailQuery = usePromiseDetail(id);
  const patchMutation = usePatchPromise(id);
  const verifyMutation = useVerifyPromise(id);
  const dossierMutation = useGenerateDossier(id);

  const [dossierJobId, setDossierJobId] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState('');
  const jobQuery = useJobStatus(dossierJobId);

  useEffect(() => {
    if (detailQuery.data?.user_note !== undefined && detailQuery.data?.user_note !== null) {
      setNoteInput(detailQuery.data.user_note);
    }
  }, [detailQuery.data?.user_note]);

  if (detailQuery.isLoading) {
    return (
      <div aria-label="Loading promise detail" className="space-y-4">
        <div className="h-16 animate-pulse rounded-xl bg-white" />
        <div className="h-44 animate-pulse rounded-xl bg-white" />
      </div>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800">
        <p>{detailQuery.error?.userMessage ?? 'Promise not found.'}</p>
        <Link to="/promises" className="mt-3 inline-block font-semibold underline">
          Back to Promises
        </Link>
      </div>
    );
  }

  const p = detailQuery.data;
  const dossierReady = jobQuery.data?.status === 'completed';
  const downloadUrl = `${getApiBaseUrl()}/api/v1/dossier/${p.promise_id}/download`;

  const handleGenerateDossier = async () => {
    const res = await dossierMutation.mutateAsync();
    setDossierJobId(res.job_id);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={p.merchant_name}
        subtitle={`Promised on ${p.created_at.slice(0, 10)} · ${(p.category ?? 'other').replace('_', ' ')}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status as PromiseStatus} />
            {p.escalation_rung && <EscalationRungBadge rung={p.escalation_rung} />}
            <Link
              to={`/merchants/${p.merchant_id}`}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Merchant Record
            </Link>
          </div>
        }
      />

      {p.needs_review_reason && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
        >
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Needs Manual Review</p>
            <p className="mt-0.5 text-xs">{p.needs_review_reason}</p>
          </div>
        </div>
      )}

      {/* Summary & Source-Quote Evidence */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Source-Quote Evidence</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Promised Amount</dt>
              <dd className="mt-1 text-lg font-bold text-slate-900">
                <AmountDisplay paise={p.amount_paise} />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Due Date (IST)</dt>
              <dd className="mt-1 font-medium text-slate-900">
                <DateDisplay iso={p.due_date} />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Extraction Method</dt>
              <dd className="mt-1 capitalize font-medium text-slate-800">{p.extraction_method}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Confidence</dt>
              <dd className="mt-1">
                <ConfidenceMeter value={p.confidence ?? 0} />
              </dd>
            </div>
          </dl>

          {p.source_email_subject && (
            <p className="mt-4 text-xs text-slate-500">
              Email Subject: <span className="font-medium text-slate-700">{p.source_email_subject}</span>
            </p>
          )}

          <blockquote className="mt-3 rounded-lg border-l-4 border-brand-500 bg-slate-50 p-3 text-sm italic text-slate-800">
            "{p.exact_quote}"
          </blockquote>
        </section>

        {/* Verification & Dossier */}
        <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Bank Credit Verification</h2>
            <button
              type="button"
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${verifyMutation.isPending ? 'animate-spin' : ''}`} />
              {verifyMutation.isPending ? 'Verifying...' : 'Re-verify'}
            </button>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            {p.status === 'kept' ? (
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 className="h-4 w-4" />
                <span>
                  Verified kept · Received{' '}
                  <AmountDisplay paise={p.received_amount_paise ?? p.amount_paise} />
                </span>
              </div>
            ) : p.received_amount_paise ? (
              <div className="flex items-center gap-2 text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                <span>
                  Partial/ambiguous credit detected:{' '}
                  <AmountDisplay paise={p.received_amount_paise} /> vs{' '}
                  <AmountDisplay paise={p.amount_paise} /> expected
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-600">
                <AlertCircle className="h-4 w-4" />
                <span>No matching bank credit verified yet.</span>
              </div>
            )}
          </div>

          <div className="border-t border-slate-100 pt-4">
            <h3 className="text-sm font-semibold text-slate-900">Evidence Dossier PDF</h3>
            <p className="mt-1 text-xs text-slate-500">
              Compile the promise quote, timeline, and escalation history into a printable PDF.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleGenerateDossier}
                disabled={dossierMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                <FileText className="h-3.5 w-3.5" />
                {dossierMutation.isPending ? 'Queueing...' : 'Generate Dossier PDF'}
              </button>

              {dossierJobId && !dossierReady && (
                <span className="text-xs text-slate-500">
                  Building PDF ({jobQuery.data?.status ?? 'queued'})...
                </span>
              )}

              {dossierReady && (
                <a
                  href={downloadUrl}
                  download={`hisaab-dossier-${p.promise_id}.pdf`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download PDF
                </a>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Escalation Ladder + Draft Viewer */}
      <EscalationLadder promiseId={p.promise_id} merchantName={p.merchant_name} />

      {/* Timeline + Notes */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Timeline</h2>
          <ol className="mt-4 space-y-4 border-l-2 border-slate-200 pl-4">
            {p.timeline.map((evt) => (
              <li key={evt.event_id} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-brand-600" />
                <p className="text-sm font-medium text-slate-900">{evt.description}</p>
                <p className="text-xs text-slate-500">
                  <DateDisplay iso={evt.occurred_at} format="datetime" />
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Personal Notes & Actions</h2>
          <textarea
            rows={4}
            value={noteInput}
            onChange={(e) => setNoteInput(e.target.value)}
            placeholder="Add a note (e.g., call reference number)..."
            className="mt-3 block w-full rounded-lg border border-slate-300 p-3 text-sm text-slate-900"
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => patchMutation.mutate({ user_note: noteInput })}
              disabled={patchMutation.isPending}
              className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Save Note
            </button>
            {p.status !== 'dismissed' && (
              <button
                type="button"
                onClick={() => patchMutation.mutate({ status: 'dismissed' })}
                disabled={patchMutation.isPending}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Dismiss Promise
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
