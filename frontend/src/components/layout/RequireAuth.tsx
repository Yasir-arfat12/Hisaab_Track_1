import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthMe } from '../../hooks/useAuth';

export function RequireAuth() {
  const location = useLocation();
  const { data: user, isLoading, isError } = useAuthMe();

  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Checking session"
        className="flex min-h-screen items-center justify-center bg-slate-50"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (isError || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
