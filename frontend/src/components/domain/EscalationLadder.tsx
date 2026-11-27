import { useState } from 'react';
import { AlertTriangle, Check, Copy, ExternalLink, Info, Sparkles } from 'lucide-react';
import { ApiError } from '../../api/fetcher';
import { useEscalationNextStep, useGenerateEscalationDraft } from '../../hooks/usePromiseDetail';
import { DateDisplay, EscalationRungBadge } from './DesignTokens';

const RUNGS = [
  { rung: 1, label: 'Polite Nudge', window: 'Days 0–7 overdue' },
  { rung: 2, label: 'Formal Grievance Notice', window: 'Days 8–21 overdue' },
  { rung: 3, label: 'NCH / Ombudsman Complaint', window: 'Days 22–45 overdue' },
  { rung: 4, label: 'Consumer Commission Notice', window: '46+ days overdue' },
];

function extractSubjectAndBody(text: string, merchantName: string): { subject: string; body: string } {
  const lines = text.split('\n');
  if (lines[0]?.toLowerCase().startsWith('subject:')) {
    const subject = lines[0].slice(8).trim();
    const body = lines.slice(1).join('\n').trim();
    return { subject, body };
  }
  return {
    subject: `Follow-up regarding pending promise — ${merchantName}`,
    body: text,
  };
}

export function EscalationLadder({
  promiseId,
  merchantName,
}: {
  promiseId: string;
  merchantName: string;
}) {
  const nextStep = useEscalationNextStep(promiseId);
  const draftMutation = useGenerateEscalationDraft(promiseId);

  const [selectedRung, setSelectedRung] = useState<number | null>(null);
  const [tone, setTone] = useState<'firm' | 'polite'>('firm');
  const [includeLegal, setIncludeLegal] = useState(false);
  const [editedDraft, setEditedDraft] = useState('');
  const [copied, setCopied] = useState(false);

  const activeRung = selectedRung ?? nextStep.data?.next_rung ?? 1;

  const handlePrepareDraft = async () => {
    const res = await draftMutation.mutateAsync({
      rung: activeRung,
      tone,
      include_legal_references: includeLegal,
    });
    setEditedDraft(res.draft_text);
    setCopied(false);
  };

  const handleCopy = async () => {
    if (!editedDraft) return;
    await navigator.clipboard.writeText(editedDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const { subject, body } = extractSubjectAndBody(editedDraft, merchantName);
  const mailtoHref = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <section
      aria-label="Escalation Ladder"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Escalation Ladder</h2>
          <p className="text-xs text-slate-500">
            Deterministic IST deadline math. You review, copy, and send every message yourself.
          </p>
        </div>
        {nextStep.data && <EscalationRungBadge rung={nextStep.data.next_rung} />}
      </div>

      {nextStep.data && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
          <p className="font-semibold text-slate-900">
            Recommended next step: {nextStep.data.rung_name}
          </p>
          <p className="mt-1">{nextStep.data.rung_description}</p>
          <p className="mt-1 text-slate-500">
            Target deadline: <DateDisplay iso={nextStep.data.deadline_date} /> (
            {nextStep.data.days_until_deadline} days)
            {nextStep.data.legal_forum ? ` · Forum: ${nextStep.data.legal_forum}` : ''}
          </p>
        </div>
      )}

      {/* 4-Rung selector */}
      <ol className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {RUNGS.map((item) => {
          const isSelected = activeRung === item.rung;
          return (
            <li key={item.rung}>
              <button
                type="button"
                onClick={() => setSelectedRung(item.rung)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  isSelected
                    ? 'border-brand-600 bg-brand-50'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <div className="text-xs font-bold text-slate-900">
                  Rung {item.rung}: {item.label}
                </div>
                <div className="mt-0.5 text-[11px] text-slate-500">{item.window}</div>
              </button>
            </li>
          );
        })}
      </ol>

      {/* Draft controls */}
      <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-4">
        <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
          Tone
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value as 'firm' | 'polite')}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
          >
            <option value="firm">Firm</option>
            <option value="polite">Polite</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
          <input
            type="checkbox"
            checked={includeLegal}
            onChange={(e) => setIncludeLegal(e.target.checked)}
            className="rounded border-slate-300 text-brand-600"
          />
          Cite Consumer Protection Act
        </label>

        <button
          type="button"
          onClick={handlePrepareDraft}
          disabled={draftMutation.isPending}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {draftMutation.isPending ? 'Preparing Draft...' : `Prepare Rung ${activeRung} Draft`}
        </button>
      </div>

      {draftMutation.isError && (
        <div role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700">
          {draftMutation.error instanceof ApiError
            ? draftMutation.error.userMessage
            : draftMutation.error.message}
        </div>
      )}

      {/* Editable Draft Viewer */}
      {editedDraft && (
        <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-800">
            <Info className="h-4 w-4 shrink-0" />
            <span>
              <strong>You send every message yourself.</strong> Hisaab prepares the draft for you to
              review, edit, copy, or open in your own email app.
            </span>
          </div>

          <label className="block text-xs font-medium text-slate-700">
            Editable Draft
            <textarea
              rows={8}
              value={editedDraft}
              onChange={(e) => setEditedDraft(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-3 font-mono text-xs text-slate-900"
            />
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copied' : 'Copy Draft'}
            </button>

            <a
              href={mailtoHref}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open in Email App (mailto)
            </a>
          </div>

          {draftMutation.data?.not_legal_advice_notice && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{draftMutation.data.not_legal_advice_notice}</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
