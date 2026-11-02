import { NavLink } from 'react-router'

import { ROLE_LABELS, type User } from '@/auth/types'
import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import { Avatar } from './Avatar'
import { Brand } from './Brand'
import type { NavItem } from './nav'

export function Sidebar({ items, user }: { items: NavItem[]; user: User | null }) {
  return (
    <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-surface desk:flex">
      <div className="flex h-16 flex-none items-center border-b border-line px-5">
        <Brand />
      </div>
      <nav aria-label="Main" className="grid flex-1 content-start gap-0.5 overflow-y-auto p-3">
        <span className="px-3 pt-2 pb-2 text-xs font-medium text-faint">Menu</span>
        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'group flex h-9 items-center gap-3 rounded-lg px-3 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-ink',
                isActive && 'bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent',
              )
            }
          >
            <Icon name={item.icon} className="size-[18px] flex-none" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="flex flex-none items-center gap-3 border-t border-line px-4 py-3.5">
          <Avatar name={user.full_name} />
          <span className="min-w-0">
            <b className="block truncate text-sm font-semibold">{user.full_name}</b>
            <span className="block truncate text-xs text-faint">{ROLE_LABELS[user.role]}</span>
          </span>
        </div>
      )}
    </aside>
  )
}
