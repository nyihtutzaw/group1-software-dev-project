import { Link, useLocation, useNavigate } from 'react-router'

import { ROLE_LABELS, type User } from '@/auth/types'
import { useAuth } from '@/auth/useAuth'
import { Icon } from '@/components/ui'

import { Avatar } from './Avatar'
import { Brand } from './Brand'
import type { NavItem } from './nav'
import { iconButton, ThemeToggle } from './ThemeToggle'

/** The menu entry the current page belongs to (project pages sit under Home). */
function sectionFor(items: NavItem[], pathname: string): NavItem | undefined {
  const exact = items.find((item) => item.path === pathname)
  if (exact) return exact
  const nested = items
    .filter((item) => item.path !== '/' && pathname.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return (
    nested ?? (pathname.startsWith('/projects/') ? items.find((i) => i.path === '/') : undefined)
  )
}

const bar =
  'sticky top-0 z-20 flex h-14 items-center gap-2.5 border-b border-line bg-surface/90 px-4 backdrop-blur-md desk:h-16 desk:px-8'

export function TopBar({ user, items }: { user: User | null; items: NavItem[] }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const section = sectionFor(items, pathname)

  const crumbs = (
    <div className="hidden min-w-0 flex-1 items-center gap-2 text-sm desk:flex">
      <span className="text-faint">CRVR</span>
      {section && (
        <>
          <Icon name="chevron" strokeWidth={2} className="size-3.5 text-faint" />
          <span className="truncate font-medium text-ink">{section.label}</span>
        </>
      )}
    </div>
  )

  if (!user) {
    return (
      <header className={bar}>
        <div className="flex-1 desk:hidden">
          <Brand />
        </div>
        {crumbs}
        <ThemeToggle />
        <Link
          to="/login"
          className="rounded-lg bg-accent px-3.5 py-2 text-sm font-semibold text-on-accent shadow-card hover:bg-accent-ink"
        >
          Sign in
        </Link>
      </header>
    )
  }

  const onLogout = () =>
    logout.mutate(undefined, { onSuccess: () => navigate('/login', { replace: true }) })

  return (
    <header className={bar}>
      <div className="min-w-0 flex-1 desk:hidden">
        <Brand />
      </div>
      {crumbs}
      <ThemeToggle />
      <button type="button" className={iconButton} title="Notifications" aria-label="Notifications">
        <Icon name="bell" strokeWidth={2} className="size-[17px]" />
      </button>
      <span className="mx-1 hidden h-6 w-px bg-line desk:block" aria-hidden="true" />
      <div className="flex items-center gap-2.5">
        <Avatar name={user.full_name} className="desk:hidden" />
        <span className="hidden text-right leading-tight desk:block">
          <b className="block max-w-56 truncate text-sm font-semibold">{user.full_name}</b>
          <span className="block max-w-56 truncate text-xs text-faint">
            {user.organization ?? ROLE_LABELS[user.role]}
          </span>
        </span>
      </div>
      <button
        type="button"
        className={iconButton}
        title="Sign out"
        aria-label="Sign out"
        onClick={onLogout}
      >
        <Icon name="logout" strokeWidth={2} className="size-[17px]" />
      </button>
    </header>
  )
}
