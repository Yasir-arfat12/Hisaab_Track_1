import { expect, test } from '@playwright/test';

test('end-to-end Hisaab user journey on MSW mocks', async ({ page }) => {
  // 1. Landing -> Demo Mode Login -> Dashboard
  await page.goto('/');
  await expect(
    page.getByText('Everyone made you a promise. Hisaab makes sure it is kept.'),
  ).toBeVisible();

  await page.getByRole('button', { name: /Try Demo Mode/i }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText('Owed to You')).toBeVisible();
  await expect(page.getByText('₹1,18,998')).toBeVisible();

  // 2. Filter by Overdue and open HDFC Insurance Promise Detail
  await page.getByRole('button', { name: 'Overdue', exact: true }).click();
  await page.getByRole('link', { name: 'HDFC Insurance' }).first().click();
  await expect(page).toHaveURL(/\/promises\/11111111-0002-0000-0000-000000000002$/);
  await expect(page.getByText('Source-Quote Evidence')).toBeVisible();

  // 3. Escalation Ladder -> Prepare Draft -> verify no-send notice & mailto
  await page.getByRole('button', { name: /Prepare Rung 3 Draft/i }).click();
  await expect(page.getByText(/You send every message yourself/i)).toBeVisible();
  await expect(page.getByRole('link', { name: /Open in Email App/i })).toHaveAttribute(
    'href',
    /^mailto:\?subject=/,
  );

  // 4. Generate Dossier PDF -> Download link
  await page.getByRole('button', { name: /Generate Dossier PDF/i }).click();
  await expect(page.getByRole('link', { name: /Download PDF/i })).toBeVisible();

  // 5. Promises & Bank Proof -> Needs Review Queue
  await page.getByRole('link', { name: 'Promises' }).click();
  await expect(page).toHaveURL(/\/promises$/);
  await expect(page.getByText(/Needs Review Queue/i)).toBeVisible();

  // 6. Demo Simulator
  await page.getByRole('link', { name: 'Demo Simulator' }).click();
  await expect(page).toHaveURL(/\/demo$/);
  await page.getByRole('button', { name: /Run Scenario/i }).first().click();
  await expect(page.getByText(/Simulated scenario: refund_arrives/i)).toBeVisible();

  // 7. Settings
  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByText('Danger Zone — Delete Account')).toBeVisible();
});
