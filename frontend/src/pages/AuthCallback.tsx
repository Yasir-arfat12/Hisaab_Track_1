import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    if (!code || !state) {
      setErrorMsg('Missing OAuth authorization code or state.');
      return;
    }

    let cancelled = false;
    apiFetch(`/api/v1/auth/google/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`)
      .then(async () => {
        if (cancelled) return;
        await queryClient.invalidateQueries({ queryKey: queryKeys.authMe() });
        navigate('/dashboard', { replace: true });
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorMsg(
          err instanceof ApiError ? err.userMessage : 'Authentication failed. Please try again.',
        );
      });

    return () => {
      cancelled = true;
    };
  }, [searchParams, navigate, queryClient]);

  if (errorMsg) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-md rounded-xl border border-red-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-bold text-slate-900">Sign-in failed</h1>
          <p className="mt-2 text-sm text-red-600">{errorMsg}</p>
          <Link
            to="/login"
            className="mt-4 inline-block rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      role="status"
      className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      <p className="text-sm text-slate-600">Completing sign-in...</p>
    </div>
  );
}
