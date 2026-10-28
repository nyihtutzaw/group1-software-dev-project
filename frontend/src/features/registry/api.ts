import { useQuery } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { api } from '@/lib/api'

export type Credit = {
  id: number
  serial: string
  project_reference: string
  project_name: string
  country: string
  methodology: string
  vintage: number
  quantity: number
  verification_status: 'approved'
  status: 'active' | 'retired' | 'revoked'
  verifier_name: string
  verification_reference: string
  approval_reference: string
  signed_off_at: string
  issued_at: string
}

export type CreditPage = { items: Credit[]; total: number; page: number; page_size: number }
export type CreditDetail = Credit & {
  history: { action: 'issued' | 'retired' | 'revoked'; occurred_at: string }[]
  monitoring: 'not_available'
  ledger_status: 'not_available'
}
export type EvidencePack = {
  serial: string
  items: { id: number; title: string; summary: string }[]
  notice: string
}
export type Integrity = {
  snapshot_matches: boolean
  ledger_status: 'not_available'
  notice: string
}

export function useCredits(q: string, page: number) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['registry', user?.id ?? null, user?.role ?? null, 'credits', q, page],
    queryFn: () =>
      api.get<CreditPage>(`/registry/credits?${new URLSearchParams({ q, page: String(page) })}`),
  })
}

export function useCredit(id: number | null) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['registry', user?.id ?? null, user?.role ?? null, 'credit', id],
    queryFn: () => api.get<CreditDetail>(`/registry/credits/${id}`),
    enabled: id !== null,
  })
}
