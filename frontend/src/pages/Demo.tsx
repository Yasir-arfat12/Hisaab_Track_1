import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Lock, Play } from 'lucide-react';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import { PageHeader } from '../components/layout/AppShell';
import { useAuthMe } from '../hooks/useAuth';
import type { DemoScenario, DemoSimulateResult } from '../types';

const SCENARIOS: { id: DemoScenario; title: string; desc: string }[] = [
  {
    id: 'refund_arrives',
    title: 'Refund Arrives',
    desc: 'Injects a matching bank credit and flips an open promise to kept.',
  },
  {
    id: 'refund_delayed',
    title: 'Refund Delayed',
    desc: 'Pushes a promise past its due date and marks it overdue for escalation.',
  },
  {
    id: 'fake_promise',
    title: 'Fake Promise Email (Prompt Injection)',
    desc: 'Injects a prompt-injection email flagged needs_review with 0.0 confidence.',
  },
  {
    id: 'duplicate_charge',
    title: 'Duplicate Charge',
    desc: 'Injects a duplicate charge promise and marks it dismissed/flagged.',
  },
];

export function DemoPage() {
  const queryClient = useQueryClient();
  const { data: user } = useAuthMe();
  const simulate = useMutation<DemoSimulateResult, ApiError, DemoScenario>({
    mutationFn: (scenario) =>
      apiFetch<DemoSimulateResult>('/api/v1/demo/simulate', {
        method: 'POST',
        body: JSON.stringify({ scenario }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['promises'] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
    },
  });

  if (user && !user.is_demo) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Demo Simulator"
          subtitle="Trigger deterministic scenarios against your demo account."
        />
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm"
        >
          <Lock className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
          <div>
            <p className="font-semibold text-slate-900">
              Demo Simulator is only available in Demo Mode
            </p>
            <p className="mt-1 text-xs text-slate-500">
              To protect your real data, synthetic scenario simulation is disabled on Google OAuth
              accounts. Sign out and choose Demo Mode to explore the simulator.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Demo Simulator"
        subtitle="Trigger deterministic scenarios against your demo account."
      />

      {simulate.isError && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {simulate.error.userMessage}
        </div>
      )}

      {simulate.data && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          <strong>{simulate.data.scenario}:</strong> {simulate.data.description}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {SCENARIOS.map((s) => (
          <div key={s.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">{s.title}</h2>
            <p className="mt-1 text-xs text-slate-500">{s.desc}</p>
            <button
              type="button"
              onClick={() => simulate.mutate(s.id)}
              disabled={simulate.isPending}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" />
              Run Scenario
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
