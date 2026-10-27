import { NavLink } from 'react-router'

import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import type { NavItem } from './nav'

/** Phone tab bar — hidden on desktop, where the sidebar takes over. */
export function BottomNav({ items }: { items: NavItem[] }) {
  return (
    <nav
      aria-label="Sections"
      className="fixed inset-x-0 bottom-0 z-30 grid auto-cols-fr grid-flow-col border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] shadow-[0_-2px_14px_rgba(11,20,18,0.06)] desk:hidden"
    >
      {items.map((item) => (
        <NavLink
          key={item.id}
          to={item.path}
          end={item.path === '/'}
          className={({ isActive }) =>
            cn(
              'grid h-[62px] place-items-center content-center gap-[3px] text-[10.5px] font-medium text-faint',
              isActive && 'font-semibold text-accent',
            )
          }
        >
          <Icon name={item.icon} className="size-[21px]" />
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
