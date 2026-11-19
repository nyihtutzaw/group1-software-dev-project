import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { api } from '@/lib/api'

// Mirrors backend/app/features/audit/demo_data.py (DemoDataOut, DemoResetIn).
export type DemoStart = 'live' | 'full'

export type DemoData = {
  /** False on a real registry: the server refuses to reset. */
  enabled: boolean
  counts: {
    users: number
    projects: number
    boundaries: number
    credits: number
    ledger_entries: number
  }
}

const KEY = ['admin', 'demo-data'] as const

export function useDemoData() {
  const { user } = useAuth()
  return useQuery({
    queryKey: KEY,
    queryFn: () => api.get<DemoData>('/admin/demo-data'),
    enabled: user?.role === 'admin',
  })
}

export function useResetDemoData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { start: DemoStart; confirm: string }) =>
      api.post<DemoData>('/admin/demo-data/reset', body),
    onSuccess: (data) => {
      // Everything cached describes data that no longer exists.
      qc.invalidateQueries()
      qc.setQueryData(KEY, data)
    },
  })
}
