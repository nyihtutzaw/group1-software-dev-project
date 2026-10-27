import type { Role } from '@/auth/types'
import type { IconName } from '@/components/ui'

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
}

const ALL: Role[] = ['developer', 'verifier', 'registry_staff', 'buyer', 'admin']

// The single source of truth for menus (sidebar + bottom bar) and route guards.
export const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', path: '/', icon: 'home', roles: ALL, feature: 'F1' },
  {
    id: 'submit',
    label: 'Submit',
    path: '/projects/new',
    icon: 'submit',
    roles: ['developer', 'admin'],
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
]

/** Menu items for a role, or the public items when nobody is signed in. */
export function navFor(role: Role | null): NavItem[] {
  return NAV_ITEMS.filter((item) => (role ? item.roles.includes(role) : item.public))
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
