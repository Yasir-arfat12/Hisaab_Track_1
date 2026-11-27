import { useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, ListChecks, LogOut, Menu, Settings, Sparkles, X } from 'lucide-react';
import { useAuthMe, useLogout } from '../../hooks/useAuth';
import { GlobalApiBanner } from './GlobalApiBanner';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/promises', label: 'Promises', icon: ListChecks },
  { to: '/demo', label: 'Demo Simulator', icon: Sparkles },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function AppShell({ children }: { children?: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { data: user } = useAuthMe();
  const logout = useLogout();

  const handleLogout = async () => {
    await logout.mutateAsync();
    navigate('/login', { replace: true });
  };

  const navItems = NAV_ITEMS.filter((item) => item.to !== '/demo' || Boolean(user?.is_demo));

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col md:flex-row">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-600 focus:px-3 focus:py-2 focus:text-xs focus:font-semibold focus:text-white"
      >
        Skip to main content
      </a>
      {/* Mobile top bar */}
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
        <Link to="/dashboard" className="text-lg font-bold text-brand-600">
          Hisaab
        </Link>
        <button
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((prev) => !prev)}
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {/* Sidebar */}
      <aside
        className={`${
          mobileOpen ? 'flex' : 'hidden'
        } w-full flex-col justify-between border-b border-slate-200 bg-white md:flex md:w-64 md:shrink-0 md:border-b-0 md:border-r`}
      >
        <div>
          <div className="hidden px-6 py-5 md:block">
            <Link to="/dashboard" className="text-xl font-extrabold tracking-tight text-brand-600">
              Hisaab
            </Link>
            <p className="mt-1 text-xs text-slate-500">Every promise tracked.</p>
          </div>

          <nav aria-label="Main navigation" className="space-y-1 px-3 py-3">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="border-t border-slate-200 p-4">
          {user && (
            <div className="mb-3">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-medium text-slate-900">{user.display_name}</p>
                {user.is_demo && (
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-800">
                    Demo
                  </span>
                )}
              </div>
              <p className="truncate text-xs text-slate-500">{user.email}</p>
            </div>
          )}
          <button
            type="button"
            onClick={handleLogout}
            disabled={logout.isPending}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            {logout.isPending ? 'Signing out...' : 'Sign out'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main id="main-content" className="flex-1 px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <GlobalApiBanner />
          {children ?? <Outlet />}
        </div>
      </main>
    </div>
  );
}
