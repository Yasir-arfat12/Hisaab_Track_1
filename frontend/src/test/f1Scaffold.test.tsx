import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ApiError, apiFetch } from '../api/fetcher';
import { AppRoutes } from '../App';
import { AmountDisplay, StatusBadge } from '../components/domain/DesignTokens';
import { server } from '../mocks/server';
import type { DashboardSummary } from '../types';

describe('F1 Scaffold', () => {
  it('parses the {data, error} envelope from MSW handlers', async () => {
    const summary = await apiFetch<DashboardSummary>('/api/v1/dashboard/summary');
    expect(summary.counts.total).toBe(8);
    expect(summary.total_overdue_paise).toBe(1565000);
  });

  it('maps contract error codes to user-friendly ApiError messages', async () => {
    server.use(
      http.get('*/api/v1/auth/me', () =>
        HttpResponse.json(
          {
            data: null,
            error: {
              code: 'GMAIL_AUTH_EXPIRED',
              message: 'Raw backend message',
              details: {},
            },
          },
          { status: 401 },
        ),
      ),
    );

    await expect(apiFetch('/api/v1/auth/me')).rejects.toThrowError(ApiError);
    try {
      await apiFetch('/api/v1/auth/me');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.code).toBe('GMAIL_AUTH_EXPIRED');
      expect(apiErr.userMessage).toContain('Gmail access has expired');
    }
  });

  it('renders design tokens and app shell navigation', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AppRoutes />
          <StatusBadge status="overdue" />
          <AmountDisplay paise={249900} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Overdue')).toBeInTheDocument();
    expect(screen.getByText('₹2,499')).toBeInTheDocument();
  });
});
