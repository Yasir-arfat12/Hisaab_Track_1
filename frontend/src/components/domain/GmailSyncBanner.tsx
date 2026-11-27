import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Mail, RefreshCw } from 'lucide-react';
import { ApiError } from '../../api/fetcher';
import { queryKeys } from '../../api/queryKeys';
import { useJobStatus } from '../../hooks/usePromiseDetail';
import { useGmailConnect, useGmailStatus, useGmailSync } from '../../hooks/useSyncAndCredits';
import { DateDisplay } from './DesignTokens';

export function GmailSyncBanner() {
  const queryClient = useQueryClient();
  const statusQuery = useGmailStatus();
  const connectMutation = useGmailConnect();
  const syncMutation = useGmailSync();

  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);
  const activeJobId = trackedJobId ?? statusQuery.data?.active_job_id ?? null;
  const jobQuery = useJobStatus(activeJobId);

  useEffect(() => {
    if (jobQuery.data?.status === 'completed') {
      void queryClient.invalidateQueries({ queryKey: ['promises'] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.syncStatus() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.credits() });
    }
  }, [jobQuery.data?.status, queryClient]);

  const handleConnect = async () => {
    const res = await connectMutation.mutateAsync();
    window.location.assign(res.redirect_url);
  };

  const handleSync = async () => {
    try {
      const res = await syncMutation.mutateAsync();
      setTrackedJobId(res.job_id);
    } catch (err) {
      if (err instanceof ApiError && err.code === 'SYNC_IN_PROGRESS') {
        const existingId = err.details.job_id;
        if (typeof existingId === 'string') {
          setTrackedJobId(existingId);
        }
      }
    }
  };

  const isRunning =
    jobQuery.data?.status === 'queued' ||
    jobQuery.data?.status === 'running' ||
    statusQuery.data?.sync_status === 'queued' ||
    statusQuery.data?.sync_status === 'running';

  const authExpired =
    syncMutation.error instanceof ApiError && syncMutation.error.code === 'GMAIL_AUTH_EXPIRED';

  const isConnected = Boolean(statusQuery.data?.connected) && !authExpired;

  return (
    <section
      aria-label="Gmail Sync"
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-brand-50 p-2 text-brand-600">
            <Mail className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {isConnected
                ? `Gmail Connected (${statusQuery.data?.email ?? 'Active'})`
                : 'Connect Gmail (Read-Only)'}
            </h2>
            <p className="text-xs text-slate-500">
              {isConnected ? (
                <>
                  {statusQuery.data?.emails_processed ?? 0} emails scanned
                  {statusQuery.data?.last_synced_at && (
                    <>
                      {' · Last synced '}
                      <DateDisplay iso={statusQuery.data.last_synced_at} format="datetime" />
                    </>
                  )}
                </>
              ) : (
                'Scan the last 90 days of refund, insurance, and bank-alert emails.'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isConnected ? (
            <button
              type="button"
              onClick={handleConnect}
              disabled={connectMutation.isPending}
              className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {connectMutation.isPending ? 'Connecting...' : 'Connect Gmail'}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSync}
              disabled={syncMutation.isPending || isRunning}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRunning ? 'animate-spin' : ''}`} />
              {isRunning ? 'Syncing...' : 'Sync Gmail'}
            </button>
          )}
        </div>
      </div>

      {authExpired && (
        <div
          role="alert"
          className="mt-3 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{syncMutation.error?.userMessage}</span>
        </div>
      )}

      {activeJobId && jobQuery.data && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-700">
              Sync Job: <span className="capitalize">{jobQuery.data.status}</span>
            </span>
            <span className="font-mono text-slate-600">{jobQuery.data.progress_pct ?? 0}%</span>
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full bg-brand-600 transition-all"
              style={{ width: `${jobQuery.data.progress_pct ?? 0}%` }}
            />
          </div>
          {jobQuery.data.status === 'completed' && (
            <div className="mt-2 flex items-center gap-1.5 text-green-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Sync completed! Promises and credits refreshed.</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
