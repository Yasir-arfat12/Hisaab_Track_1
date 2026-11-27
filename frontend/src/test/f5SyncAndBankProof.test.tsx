import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AppRoutes } from '../App';
import { server } from '../mocks/server';

function renderPromisesPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/promises']}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('F5 Sync & Bank Proof', () => {
  it('supports Connect Gmail flow when disconnected and job-polled Sync Gmail when connected', async () => {
    const user = userEvent.setup();
    const connectSpy = vi.fn();
    server.use(
      http.post('*/api/v1/gmail/connect', () => {
        connectSpy();
        return HttpResponse.json({
          data: { redirect_url: '#mock-oauth' },
          error: null,
        });
      }),
    );

    renderPromisesPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Connect Gmail' })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Connect Gmail' }));
    await waitFor(() => {
      expect(connectSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('polls sync job to completion when Gmail is connected', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('*/api/v1/gmail/status', () =>
        HttpResponse.json({
          data: {
            connected: true,
            email: 'rahul@example.com',
            last_synced_at: '2026-11-25T23:00:00Z',
            sync_status: 'idle',
            active_job_id: null,
            emails_processed: 42,
          },
          error: null,
        }),
      ),
    );

    renderPromisesPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sync Gmail/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Sync Gmail/i }));

    await waitFor(() => {
      expect(screen.getByText(/Sync completed!/i)).toBeInTheDocument();
    });
  });

  it('validates CSV columns client-side before upload and uploads valid CSV', async () => {
    const user = userEvent.setup();
    const uploadSpy = vi.fn();
    server.use(
      http.post('*/api/v1/credits/upload', () => {
        uploadSpy();
        return HttpResponse.json({
          data: { job_id: 'job-csv-1', rows_detected: 1, status: 'queued' },
          error: null,
        });
      }),
    );

    renderPromisesPage();

    const fileInput = await screen.findByLabelText(/CSV File/i);

    // Invalid CSV missing amount and reference_number
    const badFile = new File(['date,description\n2026-11-20,FLIPKART\n'], 'bad.csv', {
      type: 'text/csv',
    });
    await user.upload(fileInput, badFile);
    await user.click(screen.getByRole('button', { name: /Upload & Match Credits/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/CSV is missing required column\(s\): amount, reference_number/i),
      ).toBeInTheDocument();
    });
    expect(uploadSpy).not.toHaveBeenCalled();

    // Valid CSV
    const goodFile = new File(
      ['date,description,amount,reference_number\n2026-11-20,FLIPKART,2499,FKT123\n'],
      'good.csv',
      { type: 'text/csv' },
    );
    await user.upload(fileInput, goodFile);
    await user.click(screen.getByRole('button', { name: /Upload & Match Credits/i }));

    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('renders needs_review queue and supports Confirm Match and Dismiss actions', async () => {
    const user = userEvent.setup();
    const verifySpy = vi.fn();
    const dismissSpy = vi.fn();

    server.use(
      http.post('*/api/v1/verify/:id', () => {
        verifySpy();
        return HttpResponse.json({
          data: {
            promise_id: '11111111-0005-0000-0000-000000000005',
            previous_status: 'needs_review',
            new_status: 'kept',
            matched_credit_id: 'cccc0005-0000-0000-0000-000000000005',
            amount_paise_expected: 320000,
            amount_paise_received: 320000,
            verified_at: '2026-11-26T07:10:00Z',
          },
          error: null,
        });
      }),
      http.patch('*/api/v1/promises/:id', () => {
        dismissSpy();
        return HttpResponse.json({
          data: {
            promise_id: '11111111-0007-0000-0000-000000000007',
            merchant_name: 'Unknown Merchant',
            merchant_id: 'aaaaaaaa-0007-0000-0000-000000000007',
            category: 'other',
            amount_paise: 9999900,
            status: 'dismissed',
            due_date: '2026-11-30',
            created_at: '2026-11-20T11:00:00Z',
          },
          error: null,
        });
      }),
    );

    renderPromisesPage();

    await waitFor(() => {
      expect(screen.getByText(/Needs Review Queue \(2\)/i)).toBeInTheDocument();
    });

    const confirmButtons = screen.getAllByRole('button', { name: /Confirm Match/i });
    await user.click(confirmButtons[0]);
    await waitFor(() => {
      expect(verifySpy).toHaveBeenCalledTimes(1);
    });

    const dismissButtons = screen.getAllByRole('button', { name: /Dismiss/i });
    await user.click(dismissButtons[0]);
    await waitFor(() => {
      expect(dismissSpy).toHaveBeenCalledTimes(1);
    });
  });
});
