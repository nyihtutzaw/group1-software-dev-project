import { useId, useState } from 'react'
import { NavLink, useLocation } from 'react-router'

import { ROLE_LABELS, type User } from '@/auth/types'
import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import { Avatar } from './Avatar'
import { Brand } from './Brand'
import { isUnder, menuEntries, type MenuEntry, type NavItem } from './nav'

const link =
  'group flex h-9 items-center gap-3 rounded-lg px-3 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-ink'
const activeLink = 'bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent'

function MenuLink({ item, nested = false }: { item: NavItem; nested?: boolean }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === '/'}
      className={({ isActive }) => cn(link, nested && 'pl-10', isActive && activeLink)}
    >
      {!nested && <Icon name={item.icon} className="size-[18px] flex-none" />}
      <span>{item.label}</span>
    </NavLink>
  )
}

/** Parent menu (e.g. System): a toggle that shows its child pages; open while one of them is. */
function MenuGroup({ group }: { group: Extract<MenuEntry, { kind: 'group' }> }) {
  const { pathname } = useLocation()
  const containsCurrent = group.items.some((item) => isUnder(item, pathname))
  const [open, setOpen] = useState(containsCurrent)
  const listId = useId()

  return (
    <div className="grid gap-0.5">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen(!open)}
        className={cn(link, 'w-full text-left', containsCurrent && 'text-ink')}
      >
        <Icon name={group.icon} className="size-[18px] flex-none" />
        <span className="flex-1">{group.label}</span>
        <Icon
          name="chevron"
          strokeWidth={2}
          className={cn('size-3.5 flex-none text-faint transition-transform', open && 'rotate-90')}
        />
      </button>
      <div id={listId} hidden={!open} className="grid gap-0.5">
        {group.items.map((item) => (
          <MenuLink key={item.id} item={item} nested />
        ))}
      </div>
    </div>
  )
}

export function Sidebar({ items, user }: { items: NavItem[]; user: User | null }) {
  return (
    <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-surface desk:flex">
      <div className="flex h-16 flex-none items-center border-b border-line px-5">
        <Brand />
      </div>
      <nav aria-label="Main" className="grid flex-1 content-start gap-0.5 overflow-y-auto p-3">
        <span className="px-3 pt-2 pb-2 text-xs font-medium text-faint">Menu</span>
        {menuEntries(items).map((entry) =>
          entry.kind === 'item' ? (
            <MenuLink key={entry.item.id} item={entry.item} />
          ) : (
            <MenuGroup key={entry.id} group={entry} />
          ),
        )}
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
