import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Mail, Trash2 } from 'lucide-react';
import { apiFetch, ApiError } from '../api/fetcher';
import { queryKeys } from '../api/queryKeys';
import { PageHeader } from '../components/layout/AppShell';
import { useAuthMe } from '../hooks/useAuth';

interface GmailStatus {
  connected: boolean;
  email: string | null;
  last_synced_at: string | null;
  sync_status: 'idle' | 'queued' | 'running';
  active_job_id: string | null;
  emails_processed: number;
}

export function SettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useAuthMe();
  const [confirmText, setConfirmText] = useState('');

  const gmailStatus = useQuery<GmailStatus, ApiError>({
    queryKey: queryKeys.syncStatus(),
    queryFn: () => apiFetch<GmailStatus>('/api/v1/gmail/status'),
  });

  const connectGmail = useMutation({
    mutationFn: () => apiFetch<{ redirect_url: string }>('/api/v1/gmail/connect', { method: 'POST' }),
    onSuccess: (data) => window.location.assign(data.redirect_url),
  });

  const syncGmail = useMutation({
    mutationFn: () => apiFetch('/api/v1/gmail/sync', { method: 'POST', body: JSON.stringify({}) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.syncStatus() }),
  });

  const disconnectGmail = useMutation<{ disconnected: boolean; emails_purged: number }, ApiError>({
    mutationFn: () =>
      apiFetch<{ disconnected: boolean; emails_purged: number }>('/api/v1/gmail/disconnect', {
        method: 'POST',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.syncStatus() }),
  });

  const deleteAccount = useMutation({
    mutationFn: () => apiFetch('/api/v1/auth/me', { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.clear();
      navigate('/login', { replace: true });
    },
  });

  const gmailRevokedOrDisconnected =
    !gmailStatus.data?.connected ||
    (syncGmail.error instanceof ApiError && syncGmail.error.code === 'GMAIL_AUTH_EXPIRED');

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Manage your Gmail connection and account data." />

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">Gmail Connection (Read-Only)</h2>

        {gmailRevokedOrDisconnected && (
          <div
            role="alert"
            className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Gmail access needs reconnection</p>
              <p className="text-xs">
                {syncGmail.error instanceof ApiError && syncGmail.error.code === 'GMAIL_AUTH_EXPIRED'
                  ? syncGmail.error.userMessage
                  : 'Connect your Gmail account with read-only access to sync promises.'}
              </p>
            </div>
          </div>
        )}

        {gmailStatus.data?.connected && !gmailRevokedOrDisconnected && (
          <div className="mt-3 flex items-center gap-2 text-sm text-green-700">
            <CheckCircle2 className="h-4 w-4" />
            <span>
              Connected as <strong>{gmailStatus.data.email ?? user?.email}</strong> ·{' '}
              {gmailStatus.data.emails_processed} emails scanned
            </span>
          </div>
        )}

        {disconnectGmail.data && (
          <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3 text-xs text-green-800">
            Gmail disconnected. Purged {disconnectGmail.data.emails_purged} raw email(s).
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => connectGmail.mutate()}
            disabled={connectGmail.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            <Mail className="h-3.5 w-3.5" />
            {gmailRevokedOrDisconnected ? 'Reconnect Gmail' : 'Re-authorize Gmail'}
          </button>

          {gmailStatus.data?.connected && (
            <>
              <button
                type="button"
                onClick={() => syncGmail.mutate()}
                disabled={syncGmail.isPending}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                {syncGmail.isPending ? 'Syncing...' : 'Sync Now'}
              </button>
              <button
                type="button"
                onClick={() => disconnectGmail.mutate()}
                disabled={disconnectGmail.isPending}
                className="rounded-lg border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
              >
                Disconnect & Purge Emails
              </button>
            </>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-red-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-red-700">Danger Zone — Delete Account</h2>
        <p className="mt-1 text-xs text-slate-600">
          Permanently deletes your promises, bank credits, dossiers, and revokes Gmail access.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder='Type "DELETE" to confirm'
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
          <button
            type="button"
            disabled={confirmText !== 'DELETE' || deleteAccount.isPending}
            onClick={() => deleteAccount.mutate()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete Account
          </button>
        </div>
      </section>
    </div>
  );
}
