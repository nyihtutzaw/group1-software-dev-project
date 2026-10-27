import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api } from '@/lib/api'

import type { User } from './types'

const ME = ['auth', 'me'] as const

/**
 * The signed-in user (or null) plus login/logout actions.
 * Backed by the httpOnly session cookie — the token never touches JavaScript.
 */
export function useAuth() {
  const queryClient = useQueryClient()

  const me = useQuery({
    queryKey: ME,
    queryFn: async () => {
      try {
        return await api.get<User>('/auth/me')
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null
        throw err
      }
    },
    staleTime: Infinity,
    retry: false,
  })

  const login = useMutation({
    mutationFn: (body: { email: string; password: string }) => api.post<User>('/auth/login', body),
    onSuccess: (user) => queryClient.setQueryData(ME, user),
  })

  const logout = useMutation({
    mutationFn: () => api.post<void>('/auth/logout'),
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(ME, null)
    },
  })

  return {
    user: me.data ?? null,
    isLoading: me.isPending,
    login,
    logout,
  }
}
