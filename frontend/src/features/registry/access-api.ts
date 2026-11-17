import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { api } from '@/lib/api'

export type AccessGrant = {
  project_reference: string
  project_name: string | null
  buyer_id: number
  buyer_name: string
  buyer_email: string
  buyer_organization: string | null
  buyer_active: boolean
}
export type AccessGrantIn = { project_reference: string; buyer_id: number }
export type AccessOptions = {
  buyers: { id: number; full_name: string; email: string; organization: string | null }[]
  projects: { project_reference: string; project_name: string }[]
}

const accessKey = ['registry-access'] as const
const STAFF = ['registry_staff', 'admin']

export function useAccessGrants() {
  const { user } = useAuth()
  return useQuery({
    queryKey: [...accessKey, user?.id ?? null, 'grants'],
    queryFn: () => api.get<AccessGrant[]>('/registry/access'),
    enabled: Boolean(user && STAFF.includes(user.role)),
  })
}

export function useAccessOptions() {
  const { user } = useAuth()
  return useQuery({
    queryKey: [...accessKey, user?.id ?? null, 'options'],
    queryFn: () => api.get<AccessOptions>('/registry/access/options'),
    enabled: Boolean(user && STAFF.includes(user.role)),
  })
}

export function useGrantAccess() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AccessGrantIn) => api.post<AccessGrant>('/registry/access', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accessKey }),
  })
}

export function useRevokeAccess() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ project_reference, buyer_id }: AccessGrantIn) =>
      api.delete<void>(`/registry/access/${encodeURIComponent(project_reference)}/${buyer_id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accessKey }),
  })
}
