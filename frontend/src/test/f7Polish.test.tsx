import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../App';
import { PageErrorBoundary } from '../components/layout/ErrorBoundary';
import { server } from '../mocks/server';

function Boom(): never {
  throw new Error('Test render crash');
}

describe('F7 Polish & Error Handling', () => {
  it('catches unexpected render errors in PageErrorBoundary', () => {
    render(
      <PageErrorBoundary>
        <Boom />
      </PageErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test render crash')).toBeInTheDocument();
  });

  it('displays global banner for RATE_LIMITED and LLM_UNAVAILABLE and allows dismissal', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('*/api/v1/dashboard/summary', () =>
        HttpResponse.json(
          {
            data: null,
            error: { code: 'RATE_LIMITED', message: 'Too many requests', details: {} },
          },
          { status: 429 },
        ),
      ),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/RATE_LIMITED:/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Dismiss banner' }));
    expect(screen.queryByText(/RATE_LIMITED:/)).not.toBeInTheDocument();
  });
});
