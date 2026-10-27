import { NavLink } from 'react-router'

import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import { Brand } from './Brand'
import type { NavItem } from './nav'

export function Sidebar({ items }: { items: NavItem[] }) {
  return (
    <aside className="sticky top-0 hidden h-screen overflow-y-auto border-r border-line bg-surface px-3.5 py-5 desk:block">
      <div className="mb-3 border-b border-line px-2 pb-[18px]">
        <Brand />
      </div>
      <nav aria-label="Main" className="grid gap-0.5">
        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-[11px] rounded-[9px] px-2.5 py-[9px] text-sm font-medium text-muted hover:bg-surface-2',
                isActive && 'bg-accent-soft font-semibold text-accent hover:bg-accent-soft',
              )
            }
          >
            <Icon name={item.icon} className="size-[18px] flex-none" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
