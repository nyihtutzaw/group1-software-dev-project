import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { api } from '@/lib/api'

export type Holding = {
  id: number
  serial_block: string
  first_unit: number
  last_unit: number
  quantity: number
  status: 'held' | 'retired'
  allocated_at: string
  retired_at: string | null
  beneficiary: string | null
  reason: string | null
  reporting_year: number | null
  buyer_email: string | null
}
export type Holdings = {
  quantity: number
  allocated: number
  unallocated: number
  retired: number
  items: Holding[]
}
export type Retirement = {
  serial_block: string
  quantity: number
  beneficiary: string
  reason: string
  reporting_year: number
  retired_at: string
}
export type Retirements = { quantity: number; retired_quantity: number; items: Retirement[] }
export type AllocationIn = { buyer_email: string; quantity: number }
export type RetirementIn = {
  quantity: number
  beneficiary: string
  reason: string
  reporting_year: number
}
export type RetireResult = { retired: Holding; remaining: Holding | null }

function useScope() {
  const { user } = useAuth()
  return ['registry', user?.id ?? null, user?.role ?? null] as const
}

/** Public retirement records for one batch. */
export function useRetirements(creditId: number) {
  return useQuery({
    queryKey: [...useScope(), 'retirements', creditId],
    queryFn: () => api.get<Retirements>(`/registry/credits/${creditId}/retirements`),
  })
}

/** Staff see every holding of the batch; a buyer sees only their own. */
export function useHoldings(creditId: number, enabled: boolean) {
  return useQuery({
    queryKey: [...useScope(), 'holdings', creditId],
    queryFn: () => api.get<Holdings>(`/registry/credits/${creditId}/holdings`),
    enabled,
  })
}

// Allocation and retirement change holdings, retirements and possibly the batch status.
export function useAllocate(creditId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AllocationIn) =>
      api.post<Holding>(`/registry/credits/${creditId}/holdings`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['registry'] }),
  })
}

export function useRetire() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ holdingId, body }: { holdingId: number; body: RetirementIn }) =>
      api.post<RetireResult>(`/registry/holdings/${holdingId}/retire`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['registry'] }),
  })
}
