import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../App';
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

describe('F3 Dashboard & Promises', () => {
  it('renders Owed to You summary, status badges, and promise list', async () => {
    renderAt('/dashboard');

    await waitFor(() => {
      expect(screen.getByText('Owed to You')).toBeInTheDocument();
    });
    expect(screen.getByText('₹1,18,998')).toBeInTheDocument();
    expect(screen.getAllByText('HDFC Insurance').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flipkart').length).toBeGreaterThan(0);
  });

  it('filters promise list when clicking Overdue status chip', async () => {
    const user = userEvent.setup();
    renderAt('/dashboard');

    await waitFor(() => {
      expect(screen.getAllByText('Flipkart').length).toBeGreaterThan(0);
    });

    await user.click(screen.getByRole('button', { name: 'Overdue' }));

    await waitFor(() => {
      expect(screen.queryByText('Flipkart')).not.toBeInTheDocument();
    });
    expect(screen.getAllByText('HDFC Insurance').length).toBeGreaterThan(0);
    expect(screen.getAllByText('BookMyShow').length).toBeGreaterThan(0);
  });

  it('renders empty state when no promises match and error state on API failure', async () => {
    server.use(
      http.get('*/api/v1/dashboard/summary', () =>
        HttpResponse.json(
          { data: null, error: { code: 'RATE_LIMITED', message: 'Slow down', details: {} } },
          { status: 429 },
        ),
      ),
      http.get('*/api/v1/promises', () =>
        HttpResponse.json({
          data: { items: [], next_cursor: null, prev_cursor: null, limit: 20 },
          error: null,
        }),
      ),
    );

    renderAt('/dashboard');

    await waitFor(() => {
      expect(screen.getAllByText(/Too many requests/i).length).toBeGreaterThan(0);
      expect(screen.getByText('No promises tracked yet')).toBeInTheDocument();
    });
  });
});
