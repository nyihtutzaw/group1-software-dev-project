import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import type { Queue, Review } from './api'
import { DeveloperNotes } from './DeveloperNotes'
import { VerifyPage } from './VerifyPage'

const item = {
  id: 4,
  project_id: 9,
  project_code: 'CRVR-0147',
  project_name: 'Nan Reforestation Phase II',
  verifier_name: 'Dr. Anna Weber',
  due_date: '2026-09-26',
  overdue: true,
  days_overdue: 4,
  status: 'in_review' as const,
  chip: 'OVERDUE',
  chip_tone: 'warn' as const,
}

const queue: Queue = {
  items: [item],
  assigned_count: 4,
  overdue_count: 2,
  signed_off_this_year: 1,
}

const review: Review = {
  item,
  evidence: [{ title: 'Evidence files', detail: 'No files yet.' }],
  automatic_checks: [
    { name: 'Boundary overlap', passed: false, detail: 'Auto-checked · overlap not resolved' },
  ],
  checklist: [
    {
      key: 'land_title',
      label: 'Land title matches applicant',
      source: 'Deed 442/2561',
      checked: true,
    },
    {
      key: 'boundary_overlap',
      label: 'Boundary has no overlap',
      source: 'Auto-checked',
      checked: false,
    },
    {
      key: 'baseline',
      label: 'Baseline evidence is complete',
      source: 'Field survey',
      checked: false,
    },
    {
      key: 'methodology',
      label: 'Methodology applied correctly',
      source: 'VM0047',
      checked: false,
    },
    {
      key: 'site_visit',
      label: 'Site visit completed',
      source: 'Scheduled',
      checked: false,
    },
  ],
  note: '',
  can_submit: true,
  can_decide: false,
  decision_block: null,
  report_id: null,
  approval: null,
  chain: [
    {
      id: 'assigned-4',
      kind: 'assigned',
      at: '2026-09-01T00:00:00Z',
      actor_name: 'Naree Suwan',
      summary: 'Assigned to Dr. Anna Weber · due 2026-09-26',
      note: null,
    },
  ],
}

function mockApi(pages: { queue?: Queue; review?: Review } = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = String(input)
    const method = init?.method ?? 'GET'
    if (path === '/api/verifications/queue') return Response.json(pages.queue ?? queue)
    if (path === '/api/verifications/assignments/4' && method === 'GET') {
      return Response.json(pages.review ?? review)
    }
    if (path === '/api/verifications/assignments/4/report' && method === 'POST') {
      return Response.json({
        ...review,
        can_submit: false,
        item: { ...item, status: 'signed_off', chip: 'SIGNED OFF', chip_tone: 'wait' },
      })
    }
    if (path === '/api/verifications/verifiers') return Response.json([])
    if (path === '/api/projects') return Response.json([])
    throw new Error(`Unexpected ${method} ${path}`)
  })
}

describe('Verification queue', () => {
  it('shows the assigned projects oldest-due first with the overdue flag', async () => {
    mockApi()
    renderWithProviders(<VerifyPage />, { user: makeUser('verifier') })

    expect(await screen.findByText('4 assigned to you · 2 overdue')).toBeInTheDocument()
    expect(screen.getByText('Nan Reforestation Phase II')).toBeInTheDocument()
    expect(screen.getByText('OVERDUE')).toBeInTheDocument()
    expect(screen.getByText(/Due 26 Sep/)).toBeInTheDocument()
    const panel = await screen.findByRole('region', { name: 'Open review CRVR-0147' })
    expect(
      within(panel).getByRole('checkbox', { name: /Land title matches applicant/ }),
    ).toBeChecked()
    expect(within(panel).getByText(/Auto-checked · overlap not resolved/)).toBeInTheDocument()
  })

  it('submits a sign-off with the checklist and note', async () => {
    const fetch = mockApi()
    renderWithProviders(<VerifyPage />, { user: makeUser('verifier') })
    const panel = await screen.findByRole('region', { name: 'Open review CRVR-0147' })
    await userEvent.type(
      within(panel).getByRole('textbox', { name: 'Verifier note' }),
      'Title matches the applicant.',
    )
    await userEvent.click(within(panel).getByRole('button', { name: 'Sign off' }))

    expect(fetch).toHaveBeenCalledWith(
      '/api/verifications/assignments/4/report',
      expect.objectContaining({ method: 'POST' }),
    )
    const body = JSON.parse(
      (fetch.mock.calls.find((call) => String(call[0]).endsWith('/report'))?.[1] as RequestInit)
        .body as string,
    )
    expect(body.decision).toBe('sign_off')
    expect(body.note).toBe('Title matches the applicant.')
    expect(body.checklist.land_title).toBe(true)
  })

  it('lets staff approve a sign-off with a rationale', async () => {
    const signed: Review = {
      ...review,
      can_submit: false,
      can_decide: true,
      report_id: 8,
      note: 'Ready for approval.',
      item: {
        ...item,
        status: 'signed_off',
        chip: 'SIGNED OFF',
        chip_tone: 'wait',
        overdue: false,
        days_overdue: 0,
      },
    }
    const fetch = mockApi({ review: signed })
    fetch.mockImplementation(async (input, init) => {
      const path = String(input)
      const method = init?.method ?? 'GET'
      if (path === '/api/verifications/queue') return Response.json(queue)
      if (path === '/api/verifications/assignments/4') return Response.json(signed)
      if (path === '/api/verifications/reports/8/decision') {
        return Response.json({
          ...signed,
          can_decide: false,
          approval: {
            id: 1,
            decision: 'approved',
            rationale: 'Separate reviewer.',
            approver_name: 'Naree Suwan',
            decided_at: '2026-11-01T00:00:00Z',
          },
        })
      }
      if (path === '/api/verifications/verifiers') return Response.json([])
      if (path === '/api/projects') return Response.json([])
      throw new Error(`Unexpected ${method} ${path}`)
    })
    renderWithProviders(<VerifyPage />, { user: makeUser('registry_staff') })
    expect(await screen.findByText('4 assignments · 2 overdue')).toBeInTheDocument()
    await userEvent.type(await screen.findByRole('textbox', { name: 'Rationale' }), 'Separate reviewer.')
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('Separate reviewer.')).toBeInTheDocument()
  })
})

describe('Developer notes', () => {
  it('shows the verifier note when changes were requested', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      Response.json([
        {
          project_id: 9,
          project_code: 'CRVR-0147',
          project_name: 'Nan Reforestation Phase II',
          note: 'Land title name does not match the applicant.',
          at: '2026-11-01T00:00:00Z',
        },
      ]),
    )
    renderWithProviders(<DeveloperNotes />, { user: makeUser('developer') })
    expect(
      await screen.findByText('Land title name does not match the applicant.'),
    ).toBeInTheDocument()
  })
})
