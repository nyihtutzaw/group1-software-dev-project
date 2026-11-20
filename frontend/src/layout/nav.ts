import type { Role } from '@/auth/types'
import type { IconName } from '@/components/ui'

/** Parent menus that hold child items (shown as one collapsible entry). */
export type NavGroupId = 'system'

export const NAV_GROUPS: Record<NavGroupId, { label: string; icon: IconName }> = {
  system: { label: 'System', icon: 'settings' },
}

export type NavItem = {
  id: string
  label: string
  path: string
  icon: IconName
  /** Roles that see this menu item and may open the page. */
  roles: Role[]
  /** Also reachable without signing in. */
  public?: boolean
  /** Feature that owns the page (see docs/features/). */
  feature: 'F1' | 'F2' | 'F3' | 'F4' | 'F5'
  /** Show under this parent menu instead of at the top level. */
  group?: NavGroupId
}

/** A top-level menu entry: a page, or a parent menu with its child pages. */
export type MenuEntry =
  | { kind: 'item'; item: NavItem }
  | { kind: 'group'; id: NavGroupId; label: string; icon: IconName; items: NavItem[] }

const ALL: Role[] = ['developer', 'verifier', 'registry_staff', 'buyer', 'admin']

// The single source of truth for menus (sidebar + phone drawer) and route guards.
export const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', path: '/', icon: 'home', roles: ALL, feature: 'F1' },
  {
    id: 'submit',
    label: 'Submit',
    path: '/projects/new',
    icon: 'submit',
    // Only developers register projects (the API enforces it); admins review them from Home
    roles: ['developer'],
    feature: 'F1',
  },
  {
    id: 'map',
    label: 'Map',
    path: '/boundary',
    icon: 'map',
    roles: ['developer', 'verifier', 'registry_staff', 'admin'],
    feature: 'F2',
  },
  {
    id: 'verify',
    label: 'Verify',
    path: '/verify',
    icon: 'verify',
    roles: ['verifier', 'registry_staff', 'admin'],
    feature: 'F3',
  },
  {
    id: 'registry',
    label: 'Registry',
    path: '/registry',
    icon: 'registry',
    roles: ALL,
    public: true,
    feature: 'F4',
  },
  {
    id: 'access',
    label: 'Access',
    path: '/buyer-access',
    icon: 'lock',
    // Staff grant buyers access to projects (#30); the API enforces the same roles
    roles: ['registry_staff', 'admin'],
    feature: 'F4',
  },
  {
    id: 'ledger',
    label: 'Ledger',
    path: '/ledger',
    icon: 'ledger',
    roles: ['verifier', 'registry_staff', 'buyer', 'admin'],
    feature: 'F5',
  },
  {
    id: 'users',
    label: 'Users',
    path: '/admin/users',
    icon: 'users',
    roles: ['admin'],
    feature: 'F5',
  },
  // System — admin settings, grouped under one parent menu
  {
    id: 'roles-access',
    label: 'Role & Access',
    path: '/system/roles-access',
    icon: 'shield',
    roles: ['admin'],
    feature: 'F5',
    group: 'system',
  },
  {
    id: 'demo-data',
    label: 'Demo data',
    path: '/system/demo-data',
    icon: 'layers',
    roles: ['admin'],
    feature: 'F5',
    group: 'system',
  },
  {
    id: 'assistant',
    label: 'Assistant',
    path: '/system/assistant',
    icon: 'chat',
    roles: ['admin'],
    feature: 'F5',
    group: 'system',
  },
  {
    id: 'tutorials',
    label: 'Tutorials',
    path: '/system/tutorials',
    icon: 'book',
    roles: ['admin'],
    feature: 'F5',
    group: 'system',
  },
]

/** Menu items for a role, or the public items when nobody is signed in. */
export function navFor(role: Role | null): NavItem[] {
  return NAV_ITEMS.filter((item) => (role ? item.roles.includes(role) : item.public))
}

/** Arrange menu items for display: grouped items collapse into their parent, in first-seen order. */
export function menuEntries(items: NavItem[]): MenuEntry[] {
  const entries: MenuEntry[] = []
  for (const item of items) {
    if (!item.group) {
      entries.push({ kind: 'item', item })
      continue
    }
    const group = entries.find((e) => e.kind === 'group' && e.id === item.group)
    if (group?.kind === 'group') group.items.push(item)
    else entries.push({ kind: 'group', id: item.group, ...NAV_GROUPS[item.group], items: [item] })
  }
  return entries
}

/** True when `pathname` is the item's page or one of its sub-pages. */
export function isUnder(item: NavItem, pathname: string): boolean {
  if (item.path === '/') return pathname === '/'
  return pathname === item.path || pathname.startsWith(`${item.path}/`)
}

export function navItem(id: string): NavItem {
  const item = NAV_ITEMS.find((n) => n.id === id)
  if (!item) throw new Error(`Unknown nav item: ${id}`)
  return item
}

/** Where each role lands after signing in (as in the mock-up's role switcher). */
export const START_PAGE: Record<Role, string> = {
  developer: '/',
  verifier: '/verify',
  registry_staff: '/verify',
  buyer: '/registry',
  admin: '/ledger',
}
