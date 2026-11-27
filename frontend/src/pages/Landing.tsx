import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, FileText, ShieldCheck } from 'lucide-react';
import { useAuthMe, useDemoLogin } from '../hooks/useAuth';

export function LandingPage() {
  const navigate = useNavigate();
  const { data: user } = useAuthMe();
  const demoLogin = useDemoLogin();

  const handleDemo = async () => {
    await demoLogin.mutateAsync();
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-8">
          <span className="text-xl font-extrabold tracking-tight text-brand-600">Hisaab</span>
          <div className="flex items-center gap-3">
            {user ? (
              <Link
                to="/dashboard"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Go to Dashboard
              </Link>
            ) : (
              <Link
                to="/login"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-16 sm:px-8">
        <div className="max-w-3xl">
          <span className="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
            Consumer Promise Tracker & Evidence Assistant
          </span>
          <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Everyone made you a promise. Hisaab makes sure it is kept.
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            Track refund, insurance claim, and delivery commitments from your inbox, verify them
            against independent bank credit proof, and generate escalation drafts and evidence
            dossiers — while you stay 100% in control.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              to={user ? '/dashboard' : '/login'}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
            >
              {user ? 'Open Dashboard' : 'Get Started'}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              type="button"
              onClick={handleDemo}
              disabled={demoLogin.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {demoLogin.isPending ? 'Loading Demo...' : 'Try Demo Mode'}
            </button>
          </div>
        </div>

        <section className="mt-16 grid gap-6 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <CheckCircle2 className="h-6 w-6 text-brand-600" />
            <h2 className="mt-3 text-base font-semibold text-slate-900">Verify with Bank Proof</h2>
            <p className="mt-1 text-sm text-slate-600">
              Deterministic matching against bank credit alerts and CSV statements. Ambiguous
              matches are never auto-closed.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <FileText className="h-6 w-6 text-brand-600" />
            <h2 className="mt-3 text-base font-semibold text-slate-900">
              4-Rung Escalation & Dossier
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              IST deadline tracking from polite nudge to Consumer Commission draft, plus a PDF
              evidence dossier.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <ShieldCheck className="h-6 w-6 text-brand-600" />
            <h2 className="mt-3 text-base font-semibold text-slate-900">Read-Only & Private</h2>
            <p className="mt-1 text-sm text-slate-600">
              Uses read-only Gmail access, purges raw email bodies after extraction, and never sends
              messages on your behalf.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
