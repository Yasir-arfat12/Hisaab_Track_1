import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { subscribeApiErrors, type ApiError } from '../../api/fetcher';

export function GlobalApiBanner() {
  const [bannerError, setBannerError] = useState<ApiError | null>(null);

  useEffect(() => {
    return subscribeApiErrors((err) => {
      if (err.code === 'RATE_LIMITED' || err.code === 'LLM_UNAVAILABLE') {
        setBannerError(err);
      }
    });
  }, []);

  if (!bannerError) {
    return null;
  }

  const isRateLimit = bannerError.code === 'RATE_LIMITED';

  return (
    <div
      role="alert"
      className={`mb-4 flex items-center justify-between gap-3 rounded-xl border px-4 py-3 text-xs ${
        isRateLimit
          ? 'border-red-200 bg-red-50 text-red-800'
          : 'border-amber-200 bg-amber-50 text-amber-900'
      }`}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          <strong>{bannerError.code}:</strong> {bannerError.userMessage}
        </span>
      </div>
      <button
        type="button"
        aria-label="Dismiss banner"
        onClick={() => setBannerError(null)}
        className="rounded p-1 hover:bg-black/5"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
