import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AppRoutes } from '../App';

function renderPromiseDetail(id = '11111111-0002-0000-0000-000000000002') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/promises/${id}`]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('F4 Promise Detail', () => {
  it('renders source-quote evidence, timeline, and verification status', async () => {
    renderPromiseDetail();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'HDFC Insurance' })).toBeInTheDocument();
    });
    expect(screen.getByText(/Your claim #CLM-2026-4521 of Rs\. 15,000/)).toBeInTheDocument();
    expect(screen.getByText('Promise extracted from email')).toBeInTheDocument();
    expect(screen.getByText('No matching bank credit verified yet.')).toBeInTheDocument();
  });

  it('prepares editable escalation draft with Copy, mailto, and no-send notice', async () => {
    const user = userEvent.setup();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      configurable: true,
    });

    renderPromiseDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Prepare Rung 3 Draft/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Prepare Rung 3 Draft/i }));

    await waitFor(() => {
      expect(screen.getByText(/You send every message yourself/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/does not constitute legal advice/i)).toBeInTheDocument();
    const textarea = screen.getByLabelText(/Editable Draft/i);
    await user.type(textarea, '\nThank you.');

    await user.click(screen.getByRole('button', { name: /Copy Draft/i }));
    expect(writeTextMock).toHaveBeenCalledTimes(1);

    const mailtoLink = screen.getByRole('link', { name: /Open in Email App/i });
    expect(mailtoLink.getAttribute('href')).toMatch(/^mailto:\?subject=/);

    // Ensure no button implies the app sends email automatically
    expect(screen.queryByRole('button', { name: /^Send/i })).not.toBeInTheDocument();
  });

  it('generates dossier PDF and reveals Download PDF link', async () => {
    const user = userEvent.setup();
    renderPromiseDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Dossier PDF/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Generate Dossier PDF/i }));

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Download PDF/i })).toBeInTheDocument();
    });
  });
});
