import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import type { Role } from '@/auth/types'
import { api } from '@/lib/api'

export type AdminUser = {
  id: number
  email: string
  full_name: string
  organization: string | null
  role: Role
  is_active: boolean
}

export type AdminUserCreate = {
  email: string
  full_name: string
  organization: string | null
  role: Role
  initial_password: string
}

export type AdminUserUpdate = {
  role?: Role
  is_active?: boolean
}

const usersKey = ['admin', 'users'] as const

export function useAdminUsers() {
  const { user } = useAuth()
  return useQuery({
    queryKey: [...usersKey, user?.id ?? null],
    queryFn: () => api.get<AdminUser[]>('/admin/users'),
    enabled: user?.role === 'admin',
  })
}

export function useCreateAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AdminUserCreate) => api.post<AdminUser>('/admin/users', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  })
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, changes }: { userId: number; changes: AdminUserUpdate }) =>
      api.patch<AdminUser>(`/admin/users/${userId}`, changes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  })
}
