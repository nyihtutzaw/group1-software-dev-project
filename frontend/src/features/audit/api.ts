import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'

export type LedgerEntry = {
  id: number
  created_at: string
  action: string
  actor_id: number | null
  actor_email: string | null
  actor_role: string | null
  entity: string
  entity_id: number
  payload: Record<string, unknown>
  prev_hash: string
  hash: string
}

export type LedgerPage = {
  total: number
  page: number
  page_size: number
  items: LedgerEntry[]
}

export type LedgerVerification = {
  valid: boolean
  error: string | null
}

const ledgerKey = (page: number) => ['ledger', 'entries', page] as const
const verifyKey = ['ledger', 'verify'] as const

export function useLedger(page: number) {
  return useQuery({
    queryKey: ledgerKey(page),
    queryFn: () => api.get<LedgerPage>(`/ledger?page=${page}&page_size=50`),
    placeholderData: (prev) => prev,
  })
}

export function useLedgerVerify(enabled = true) {
  return useQuery({
    queryKey: verifyKey,
    queryFn: () => api.get<LedgerVerification>('/ledger/verify'),
    staleTime: 60_000, // re-check every minute at most
    enabled,
  })
}
