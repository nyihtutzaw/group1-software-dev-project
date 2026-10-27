import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api } from '@/lib/api'

import type {
  BoundaryCheck,
  BoundaryCollection,
  Geometry,
  OverlapFlag,
  ProjectBoundary,
  ProjectSummary,
} from './types'

const KEYS = {
  all: ['boundaries'] as const,
  project: (id: number) => ['boundaries', id] as const,
}

/** Every registered boundary (the map's context layer). */
export function useBoundaries() {
  return useQuery({
    queryKey: KEYS.all,
    queryFn: () => api.get<BoundaryCollection>('/boundaries'),
  })
}

/** A project's saved boundary, or null when none is registered yet. */
export function useProjectBoundary(projectId: number | null) {
  return useQuery({
    queryKey: KEYS.project(projectId ?? 0),
    enabled: projectId !== null,
    queryFn: async () => {
      try {
        return await api.get<ProjectBoundary>(`/boundaries/${projectId}`)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null
        throw err
      }
    },
  })
}

/** Projects the user may work on (F1's list: own projects for developers, all for staff). */
export function useProjects(enabled: boolean) {
  return useQuery({
    queryKey: ['projects'],
    enabled,
    queryFn: () => api.get<ProjectSummary[]>('/projects'),
  })
}

export function useCheckBoundary() {
  return useMutation({
    mutationFn: (body: { geometry: Geometry; project_id: number | null }) =>
      api.post<BoundaryCheck>('/boundaries/check', body),
  })
}

export function useImportBoundary() {
  return useMutation({
    mutationFn: (file: File) =>
      api.upload<{ filename: string; geometry: Geometry }>('/boundaries/import', file),
  })
}

export function useSaveBoundary(projectId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { geometry: Geometry; source: 'drawn' | 'uploaded' }) =>
      api.put<ProjectBoundary>(`/boundaries/${projectId}`, body),
    onSuccess: (saved) => {
      qc.setQueryData(KEYS.project(saved.project_id), saved)
      qc.invalidateQueries({ queryKey: KEYS.all, exact: true })
    },
  })
}

function useFlagAction(action: 'dispute' | 'resolve', projectId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ flagId, text }: { flagId: number; text: string }) =>
      api.post<OverlapFlag>(
        `/boundaries/flags/${flagId}/${action}`,
        action === 'dispute' ? { reason: text } : { note: text },
      ),
    onSuccess: () => {
      if (projectId !== null) qc.invalidateQueries({ queryKey: KEYS.project(projectId) })
      qc.invalidateQueries({ queryKey: KEYS.all, exact: true })
    },
  })
}

export const useDisputeFlag = (projectId: number | null) => useFlagAction('dispute', projectId)
export const useResolveFlag = (projectId: number | null) => useFlagAction('resolve', projectId)
