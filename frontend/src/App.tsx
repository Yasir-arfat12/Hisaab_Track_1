import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { PageErrorBoundary } from './components/layout/ErrorBoundary';
import { RequireAuth } from './components/layout/RequireAuth';
import { AuthCallbackPage } from './pages/AuthCallback';
import { DashboardPage } from './pages/Dashboard';
import { DemoPage } from './pages/Demo';
import { LandingPage } from './pages/Landing';
import { LoginPage } from './pages/Login';
import { MerchantPage } from './pages/Merchant';
import { PromiseDetailPage } from './pages/PromiseDetail';
import { PromisesPage } from './pages/Promises';
import { SettingsPage } from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function AppRoutes() {
  return (
    <PageErrorBoundary>
      <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/promises" element={<PromisesPage />} />
          <Route path="/promises/:id" element={<PromiseDetailPage />} />
          <Route path="/merchants/:id" element={<MerchantPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/demo" element={<DemoPage />} />
        </Route>
      </Route>
    </Routes>
    </PageErrorBoundary>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
