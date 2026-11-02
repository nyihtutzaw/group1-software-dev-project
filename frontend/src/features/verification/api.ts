import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { type ChipTone } from '@/components/ui'
import { api } from '@/lib/api'

export type AssignmentStatus =
  'assigned' | 'in_review' | 'changes_requested' | 'signed_off' | 'approved' | 'rejected'

export type QueueItem = {
  id: number
  project_id: number
  project_code: string
  project_name: string
  verifier_name: string
  due_date: string
  overdue: boolean
  days_overdue: number
  status: AssignmentStatus
  chip: string
  chip_tone: ChipTone
}

export type Queue = {
  items: QueueItem[]
  assigned_count: number
  overdue_count: number
  signed_off_this_year: number
}

export type CheckLine = { key: string; label: string; source: string; checked: boolean }

export type Review = {
  item: QueueItem
  evidence: { title: string; detail: string }[]
  automatic_checks: { name: string; passed: boolean; detail: string }[]
  checklist: CheckLine[]
  note: string
  can_submit: boolean
  can_decide: boolean
  decision_block: string | null
  report_id: number | null
  approval: {
    id: number
    decision: 'approved' | 'rejected'
    rationale: string
    approver_name: string
    decided_at: string
  } | null
  chain: {
    id: string
    kind: 'assigned' | 'report' | 'approval'
    at: string
    actor_name: string
    summary: string
    note: string | null
  }[]
}

export type VerifierOption = { id: number; full_name: string; email: string }
export type ProjectOption = { id: number; code: string; name: string; status: string }
export type ChangeNote = {
  project_id: number
  project_code: string
  project_name: string
  /** changes_requested: the verifier's note · rejected: the registry staff rationale */
  kind: 'changes_requested' | 'rejected'
  note: string
  at: string
}

export type ReportBody = {
  checklist: Record<string, boolean>
  note: string
  decision: 'sign_off' | 'request_changes'
}

const queueKey = ['verifications', 'queue'] as const

export function useQueue() {
  const { user } = useAuth()
  return useQuery({
    queryKey: [...queueKey, user?.id ?? null],
    queryFn: () => api.get<Queue>('/verifications/queue'),
    enabled: !!user,
  })
}

export function useReview(id: number | null) {
  return useQuery({
    queryKey: ['verifications', 'review', id],
    queryFn: () => api.get<Review>(`/verifications/assignments/${id}`),
    enabled: id !== null,
  })
}

export function useVerifiers(enabled: boolean) {
  return useQuery({
    queryKey: ['verifications', 'verifiers'],
    queryFn: () => api.get<VerifierOption[]>('/verifications/verifiers'),
    enabled,
  })
}

export function useAssignableProjects(enabled: boolean) {
  return useQuery({
    queryKey: ['projects', 'assign'],
    queryFn: () => api.get<ProjectOption[]>('/projects'),
    enabled,
  })
}

export function useChangeNotes(enabled: boolean) {
  return useQuery({
    queryKey: ['verifications', 'notes'],
    queryFn: () => api.get<ChangeNote[]>('/verifications/notes'),
    enabled,
  })
}

export function useAssign() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { project_id: number; verifier_id: number; due_date: string }) =>
      api.post<QueueItem>('/verifications/assignments', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queueKey }),
  })
}

export function useSubmitReport(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReportBody) =>
      api.post<Review>(`/verifications/assignments/${id}/report`, body),
    onSuccess: (review) => {
      qc.setQueryData(['verifications', 'review', id], review)
      void qc.invalidateQueries({ queryKey: queueKey })
    },
  })
}

export function useDecide(reportId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { decision: 'approved' | 'rejected'; rationale: string }) =>
      api.post<Review>(`/verifications/reports/${reportId}/decision`, body),
    onSuccess: (review) => {
      qc.setQueryData(['verifications', 'review', review.item.id], review)
      void qc.invalidateQueries({ queryKey: queueKey })
    },
  })
}
