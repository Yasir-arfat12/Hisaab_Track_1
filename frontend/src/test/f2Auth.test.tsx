import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../App';
import { server } from '../mocks/server';

function renderAt(path: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('F2 Auth Screens', () => {
  it('renders landing page with tagline and sign in CTA', async () => {
    server.use(
      http.get('*/api/v1/auth/me', () =>
        HttpResponse.json(
          { data: null, error: { code: 'AUTH_REQUIRED', message: 'Not logged in', details: {} } },
          { status: 401 },
        ),
      ),
    );

    renderAt('/');
    expect(
      screen.getByText(/Everyone made you a promise\. Hisaab makes sure it is kept\./i),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Get Started/i })).toBeInTheDocument();
  });

  it('redirects protected routes to /login when /auth/me returns AUTH_REQUIRED', async () => {
    server.use(
      http.get('*/api/v1/auth/me', () =>
        HttpResponse.json(
          { data: null, error: { code: 'AUTH_REQUIRED', message: 'No session', details: {} } },
          { status: 401 },
        ),
      ),
    );

    renderAt('/dashboard');
    await waitFor(() => {
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    });
  });

  it('allows Demo Mode login, bootstraps /me, and signs out cleanly', async () => {
    const user = userEvent.setup();
    renderAt('/login');

    const demoBtn = screen.getByRole('button', { name: /Try Demo Mode/i });
    await user.click(demoBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    });
    expect(screen.getByText('Demo User')).toBeInTheDocument();

    const logoutBtn = screen.getByRole('button', { name: /Sign out/i });
    await user.click(logoutBtn);

    await waitFor(() => {
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    });
  });

  it('shows error card on /auth/callback when code or state is missing', async () => {
    renderAt('/auth/callback');
    await waitFor(() => {
      expect(screen.getByText('Sign-in failed')).toBeInTheDocument();
      expect(screen.getByText(/Missing OAuth authorization code/i)).toBeInTheDocument();
    });
  });
});
