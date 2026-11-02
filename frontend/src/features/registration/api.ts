import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'

import type { EvidenceKind, EvidenceOut, ProjectDetail, ProjectIn, ProjectOut } from './types'

const KEYS = {
  // Shared with F2's map picker, which reads the same list
  all: ['projects'] as const,
  project: (id: number) => ['projects', id] as const,
}

/** Own projects for developers, all projects for registry staff and admins. */
export function useProjectList(enabled = true) {
  return useQuery({
    queryKey: KEYS.all,
    enabled,
    queryFn: () => api.get<ProjectOut[]>('/projects'),
  })
}

export function useProject(id: number | null) {
  return useQuery({
    queryKey: KEYS.project(id ?? 0),
    enabled: id !== null,
    queryFn: () => api.get<ProjectDetail>(`/projects/${id}`),
  })
}

function useProjectMutation<V>(fn: (vars: V) => Promise<ProjectDetail>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (project) => {
      qc.setQueryData(KEYS.project(project.id), project)
      qc.invalidateQueries({ queryKey: KEYS.all, exact: true })
    },
  })
}

export const useCreateProject = () =>
  useProjectMutation((body: ProjectIn) => api.post<ProjectDetail>('/projects', body))

export const useUpdateProject = (id: number) =>
  useProjectMutation((body: ProjectIn) => api.put<ProjectDetail>(`/projects/${id}`, body))

export const useSubmitProject = (id: number) =>
  useProjectMutation(() => api.post<ProjectDetail>(`/projects/${id}/submit`))

/** Upload one evidence file. It is sealed by the server at once — there is no undo. */
export function useUploadEvidence(projectId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: EvidenceKind }) => {
      const form = new FormData()
      form.append('file', file)
      form.append('kind', kind)
      return api.post<EvidenceOut>(`/projects/${projectId}/evidence`, form)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.project(projectId) })
      qc.invalidateQueries({ queryKey: KEYS.all, exact: true })
    },
  })
}

export const evidenceUrl = (projectId: number, evidenceId: number) =>
  `/api/projects/${projectId}/evidence/${evidenceId}/file`
