import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AppRoutes } from '../App';
import { DEMO_USER } from '../mocks/seed/demoData';
import { server } from '../mocks/server';

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('F6 Merchant & Demo Tools', () => {
  it('renders Merchant Record stats and promise history', async () => {
    renderAt('/merchants/aaaaaaaa-0001-0000-0000-000000000001');

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Flipkart' })).toBeInTheDocument();
    });
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('13d')).toBeInTheDocument();
    expect(screen.getByText('Promise History')).toBeInTheDocument();
  });

  it('shows Demo Simulator in Demo Mode and hides/blocks it for non-demo users', async () => {
    const user = userEvent.setup();
    renderAt('/demo');

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Demo Simulator' })).toBeInTheDocument();
    });
    expect(screen.getByRole('link', { name: 'Demo Simulator' })).toBeInTheDocument();

    const runButtons = screen.getAllByRole('button', { name: /Run Scenario/i });
    await user.click(runButtons[0]);
    await waitFor(() => {
      expect(screen.getByText(/Simulated scenario: refund_arrives/i)).toBeInTheDocument();
    });

    // Switch to non-demo user
    server.use(
      http.get('*/api/v1/auth/me', () =>
        HttpResponse.json({
          data: { ...DEMO_USER, is_demo: false, gmail_connected: true },
          error: null,
        }),
      ),
    );
    renderAt('/demo');
    await waitFor(() => {
      expect(
        screen.getByText(/Demo Simulator is only available in Demo Mode/i),
      ).toBeInTheDocument();
    });
  });

  it('allows disconnecting Gmail and deleting account in Settings', async () => {
    const user = userEvent.setup();
    const deleteSpy = vi.fn();

    server.use(
      http.get('*/api/v1/gmail/status', () =>
        HttpResponse.json({
          data: {
            connected: true,
            email: 'rahul@example.com',
            last_synced_at: '2026-11-25T23:00:00Z',
            sync_status: 'idle',
            active_job_id: null,
            emails_processed: 12,
          },
          error: null,
        }),
      ),
      http.post('*/api/v1/gmail/disconnect', () =>
        HttpResponse.json({ data: { disconnected: true, emails_purged: 12 }, error: null }),
      ),
      http.delete('*/api/v1/auth/me', () => {
        deleteSpy();
        return HttpResponse.json({ data: { deleted: true }, error: null });
      }),
    );

    renderAt('/settings');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Disconnect & Purge Emails/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Disconnect & Purge Emails/i }));
    await waitFor(() => {
      expect(screen.getByText(/Purged 12 raw email\(s\)/i)).toBeInTheDocument();
    });

    const deleteBtn = screen.getByRole('button', { name: /Delete Account/i });
    expect(deleteBtn).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/Type "DELETE" to confirm/i), 'DELETE');
    expect(deleteBtn).toBeEnabled();
    await user.click(deleteBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledTimes(1);
    });
  });
});
