import { Outlet, useLocation } from 'react-router'

import { useAuth } from '@/auth/useAuth'

import { BottomNav } from './BottomNav'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { navFor } from './nav'

/**
 * Responsive shell from the mock-up: phones get a top bar + bottom tab bar,
 * screens ≥ 880px (`desk:`) get a fixed sidebar instead of the tab bar.
 */
export function AppShell() {
  const { user, isLoading } = useAuth()
  const { pathname } = useLocation()

  if (isLoading) {
    return <div className="grid min-h-screen place-items-center text-sm text-faint">Loading…</div>
  }

  const items = navFor(user?.role ?? null)

  return (
    <div className="grid min-h-screen grid-cols-1 desk:grid-cols-[248px_1fr]">
      <Sidebar items={items} user={user} />
      <div className="min-w-0 pb-[calc(62px+env(safe-area-inset-bottom))] desk:pb-0">
        <TopBar user={user} items={items} />
        {/* key forces the fade-in animation on every page change */}
        <main
          key={pathname}
          className="page-enter mx-auto max-w-[1120px] px-4 pt-5 pb-8 desk:px-8 desk:pt-8 desk:pb-12"
        >
          <Outlet />
        </main>
      </div>
      <BottomNav items={items} />
    </div>
  )
}
