import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, ShieldCheck } from 'lucide-react';
import { useDemoLogin, useGoogleStart } from '../hooks/useAuth';
import { ApiError } from '../api/fetcher';

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const googleStart = useGoogleStart();
  const demoLogin = useDemoLogin();

  const queryError = searchParams.get('error');
  const activeError =
    googleStart.error || demoLogin.error
      ? ((googleStart.error || demoLogin.error) as ApiError).userMessage
      : queryError
        ? 'Google sign-in could not be completed. Please try again.'
        : null;

  const handleGoogleSignIn = async () => {
    const data = await googleStart.mutateAsync();
    window.location.assign(data.redirect_url);
  };

  const handleDemoMode = async () => {
    await demoLogin.mutateAsync();
    navigate('/dashboard', { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="text-center">
          <span className="text-2xl font-extrabold tracking-tight text-brand-600">Hisaab</span>
          <h1 className="mt-2 text-xl font-bold text-slate-900">Sign in to your account</h1>
          <p className="mt-1 text-sm text-slate-500">
            Everyone made you a promise. Hisaab makes sure it is kept.
          </p>
        </div>

        {activeError && (
          <div
            role="alert"
            className="mt-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{activeError}</span>
          </div>
        )}

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={googleStart.isPending || demoLogin.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {googleStart.isPending ? 'Redirecting to Google...' : 'Continue with Google'}
          </button>

          <button
            type="button"
            onClick={handleDemoMode}
            disabled={googleStart.isPending || demoLogin.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {demoLogin.isPending ? 'Starting Demo Mode...' : 'Try Demo Mode (No Google Account)'}
          </button>
        </div>

        <div className="mt-6 flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
          <p>
            Hisaab requests <strong>gmail.readonly</strong> access only. We never send emails — you
            review and send every message yourself.
          </p>
        </div>
      </div>
    </div>
  );
}
