import { Link, useNavigate } from 'react-router'

import { ROLE_LABELS, type User } from '@/auth/types'
import { useAuth } from '@/auth/useAuth'
import { Icon } from '@/components/ui'

import { Brand } from './Brand'

function initials(name: string): string {
  return name
    .replace(/^Dr\.?\s+/i, '')
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

const iconButton =
  'grid size-[34px] flex-none place-items-center rounded-[9px] border border-line text-muted hover:bg-surface-2'

export function TopBar({ user }: { user: User | null }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  if (!user) {
    return (
      <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-surface px-4 py-3 desk:px-7 desk:py-3.5">
        <div className="flex-1 desk:invisible">
          <Brand />
        </div>
        <Link
          to="/login"
          className="rounded-[9px] bg-accent px-3.5 py-2 text-sm font-semibold text-on-accent"
        >
          Sign in
        </Link>
      </header>
    )
  }

  const onLogout = () =>
    logout.mutate(undefined, { onSuccess: () => navigate('/login', { replace: true }) })

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-surface px-4 py-3 desk:px-7 desk:py-3.5">
      <div className="min-w-0 flex-1">
        <b className="block truncate font-serif text-[19px] leading-tight tracking-[-0.01em]">
          {user.full_name}
        </b>
        <span className="text-xs text-faint">
          {ROLE_LABELS[user.role]}
          {user.organization && <> &middot; {user.organization}</>}
        </span>
      </div>
      <button type="button" className={iconButton} title="Notifications" aria-label="Notifications">
        <Icon name="bell" strokeWidth={2} className="size-[17px]" />
      </button>
      <button
        type="button"
        className={iconButton}
        title="Sign out"
        aria-label="Sign out"
        onClick={onLogout}
      >
        <Icon name="logout" strokeWidth={2} className="size-[17px]" />
      </button>
      <span
        className="grid size-[34px] flex-none place-items-center rounded-full bg-accent-soft font-mono text-[12.5px] font-bold text-accent"
        aria-hidden="true"
      >
        {initials(user.full_name)}
      </span>
    </header>
  )
}
