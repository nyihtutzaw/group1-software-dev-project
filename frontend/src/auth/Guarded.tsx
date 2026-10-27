import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { navItem } from '@/layout/nav'
import { ForbiddenPage } from '@/pages/ForbiddenPage'

import { useAuth } from './useAuth'

/**
 * Route guard driven by NAV_ITEMS: signed-out users go to /login (and come back after),
 * signed-in users whose role is not allowed see a 403 page.
 *
 *   <Route path="/verify" element={<Guarded page="verify"><VerifyPage /></Guarded>} />
 */
export function Guarded({ page, children }: { page: string; children: ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  const item = navItem(page)

  if (!user) {
    if (item.public) return children
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (!item.roles.includes(user.role)) return <ForbiddenPage />
  return children
}
