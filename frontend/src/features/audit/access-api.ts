import { useQuery } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import type { Role } from '@/auth/types'
import { api } from '@/lib/api'

// Mirrors backend/app/features/audit/access_matrix.py (EndpointAccessOut, AccessMatrixOut).
export type EndpointAccess = {
  method: string
  path: string
  summary: string
  /** The router's tag, e.g. "F2 boundary". */
  area: string
  /** `roles`: only `roles` may call it · `signed_in`: any signed-in user · `public`: anyone. */
  access: 'public' | 'signed_in' | 'roles'
  roles: Role[]
}

export type AccessMatrix = {
  roles: Role[]
  endpoints: EndpointAccess[]
}

export function useAccessMatrix() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['admin', 'access-matrix'],
    queryFn: () => api.get<AccessMatrix>('/admin/access-matrix'),
    enabled: user?.role === 'admin',
  })
}
