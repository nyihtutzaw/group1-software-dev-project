import { NavLink, useLocation } from 'react-router'

import { Icon, type IconName } from '@/components/ui'
import { cn } from '@/lib/cn'

import { isUnder, menuEntries, type NavItem } from './nav'

const tab =
  'grid h-[62px] place-items-center content-center gap-1 text-[11px] font-medium text-faint'
const activeTab = 'font-semibold text-accent'

/**
 * Phone tab bar — hidden on desktop, where the sidebar takes over. A parent menu (e.g. System)
 * is one tab that opens its first child page.
 */
export function BottomNav({ items }: { items: NavItem[] }) {
  const { pathname } = useLocation()
  const tabs: Tab[] = menuEntries(items).map((entry) =>
    entry.kind === 'item'
      ? { id: entry.item.id, item: entry.item, label: entry.item.label, icon: entry.item.icon }
      : {
          id: entry.id,
          item: entry.items[0],
          label: entry.label,
          icon: entry.icon,
          active: entry.items.some((item) => isUnder(item, pathname)),
        },
  )

  return (
    <nav
      aria-label="Sections"
      className="fixed inset-x-0 bottom-0 z-30 grid auto-cols-fr grid-flow-col border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md desk:hidden"
    >
      {tabs.map(({ id, item, label, icon, active }) => (
        <NavLink
          key={id}
          to={item.path}
          end={item.path === '/'}
          className={({ isActive }) => cn(tab, (active ?? isActive) && activeTab)}
        >
          <Icon name={icon} className="size-[21px]" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

/** `active` is set for a parent menu: highlighted while any of its child pages is open. */
type Tab = { id: string; item: NavItem; label: string; icon: IconName; active?: boolean }
