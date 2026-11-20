import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import type { User } from '@/auth/types'
import { makeUser, renderWithProviders } from '@/test/render'

import type { Queue, Review } from './api'
import { DeveloperNotes } from './DeveloperNotes'
import { ReviewPage } from './ReviewPage'
import { VerifyPage } from './VerifyPage'

function renderVerify(route: string, user: User) {
  return renderWithProviders(
    <Routes>
      <Route path="/verify" element={<VerifyPage />} />
      <Route path="/verify/:id" element={<ReviewPage />} />
    </Routes>,
    { route, user },
  )
}

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
  risk_rating: null,
  can_submit: true,
  can_reassign: false,
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
  buffer_percent: null,
  can_issue: false,
  issuance: null,
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
  it('groups the queue into tabs and links each assignment to its review', async () => {
    mockApi({
      queue: {
        ...queue,
        items: [
          item,
          {
            ...item,
            id: 5,
            project_name: 'Phrae Agroforestry',
            status: 'signed_off',
            chip: 'SIGNED OFF',
            chip_tone: 'wait',
          },
        ],
      },
    })
    renderVerify('/verify', makeUser('verifier'))

    expect(await screen.findByText('4 assigned to you · 2 overdue')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /In progress/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.queryByRole('tab', { name: 'Assign verifier' })).not.toBeInTheDocument()
    const row = screen.getByRole('link', { name: /Nan Reforestation Phase II/ })
    expect(row).toHaveAttribute('href', '/verify/4')
    expect(within(row).getByText('OVERDUE')).toBeInTheDocument()
    expect(within(row).getByText('4 days overdue')).toBeInTheDocument()
    expect(screen.queryByText('Phrae Agroforestry')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /Awaiting approval/ }))
    expect(screen.getByRole('link', { name: /Phrae Agroforestry/ })).toBeInTheDocument()
    expect(screen.queryByText('Nan Reforestation Phase II')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /Approved/ }))
    expect(screen.getByText('Nothing approved yet')).toBeInTheDocument()
  })

  it('gives staff an assign tab', async () => {
    mockApi()
    renderVerify('/verify', makeUser('registry_staff'))
    await userEvent.click(await screen.findByRole('tab', { name: 'Assign verifier' }))
    expect(screen.getByRole('combobox', { name: 'Project' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Assign' })).toBeDisabled()
  })

  it('opens a review with the checklist, and evidence and history in tabs', async () => {
    mockApi()
    renderVerify('/verify/4', makeUser('verifier'))

    const panel = await screen.findByRole('region', { name: 'Open review CRVR-0147' })
    expect(
      within(panel).getByRole('heading', { name: 'Nan Reforestation Phase II' }),
    ).toBeInTheDocument()
    expect(
      within(panel).getByRole('checkbox', { name: /Land title matches applicant/ }),
    ).toBeChecked()
    expect(within(panel).getByText('1 of 5 confirmed')).toBeInTheDocument()

    await userEvent.click(within(panel).getByRole('tab', { name: /Evidence & checks/ }))
    expect(within(panel).getByText(/Auto-checked · overlap not resolved/)).toBeInTheDocument()
    expect(within(panel).getByText('NEEDS ATTENTION')).toBeInTheDocument()

    await userEvent.click(within(panel).getByRole('tab', { name: /History/ }))
    expect(
      within(panel).getByText('Assigned to Dr. Anna Weber · due 2026-09-26'),
    ).toBeInTheDocument()
  })

  it('submits a sign-off with the checklist and note', async () => {
    const fetch = mockApi()
    renderVerify('/verify/4', makeUser('verifier'))
    const panel = await screen.findByRole('region', { name: 'Open review CRVR-0147' })
    await userEvent.type(
      within(panel).getByRole('textbox', { name: 'Verifier note' }),
      'Title matches the applicant.',
    )
    await userEvent.selectOptions(
      within(panel).getByRole('combobox', { name: 'Reversal risk' }),
      'medium',
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
    expect(body.risk_rating).toBe('medium')
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
      throw new Error(`Unexpected ${method} ${path}`)
    })
    renderVerify('/verify/4', makeUser('registry_staff'))
    await userEvent.type(
      await screen.findByRole('textbox', { name: 'Rationale' }),
      'Separate reviewer.',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('Approved by Naree Suwan')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
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

  it('lets registry staff issue credits after approval, then links to the registry', async () => {
    const approved: Review = {
      ...review,
      item: { ...item, status: 'approved' },
      can_submit: false,
      risk_rating: 'low',
      buffer_percent: 10,
      can_issue: true,
      approval: {
        id: 3,
        decision: 'approved',
        rationale: 'Checklist complete.',
        approver_name: 'Naree Suwan',
        decided_at: '2026-09-30T00:00:00Z',
      },
    }
    const issued: Review = {
      ...approved,
      can_issue: false,
      issuance: { credit_id: 11, vintage: 2026, quantity: 4320, buffer_quantity: 480 },
    }
    let current = approved
    const issue = vi.fn(() => {
      current = issued
      return { id: 11 }
    })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input)
      if (path === '/api/verifications/assignments/4') return Response.json(current)
      if (path === '/api/verifications/projects/9/issue' && init?.method === 'POST') {
        return Response.json(issue(), { status: 201 })
      }
      return Response.json(queue)
    })
    renderVerify('/verify/4', makeUser('registry_staff'))

    await userEvent.type(await screen.findByLabelText('Verified tonnes (tCO₂e)'), '4800')
    expect(
      screen.getByText(/480 t \(10%\) go to the buffer pool as insurance; 4,320 t can be sold/),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Issue credits' }))

    expect(await screen.findByText('4,320 credits issued for 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View on the public registry' })).toHaveAttribute(
      'href',
      '/registry/11',
    )
    expect(issue).toHaveBeenCalledTimes(1)
  })
})
