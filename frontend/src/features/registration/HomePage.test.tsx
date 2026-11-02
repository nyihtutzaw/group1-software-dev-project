import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, mockFetch, renderWithProviders } from '@/test/render'

import { HomePage } from './HomePage'
import type { ProjectOut } from './types'

const base: ProjectOut = {
  id: 1,
  code: 'CRVR-0147',
  name: 'Nan Reforestation Phase II',
  status: 'submitted',
  created_at: '2026-09-12T00:00:00Z',
  methodology: 'VM0047',
  area_ha: 1240,
  est_removal_tco2e: 24800,
  submitted_at: '2026-09-12T00:00:00Z',
  evidence_count: 3,
  overlap: true,
}
const projects: ProjectOut[] = [
  base,
  {
    ...base,
    id: 2,
    code: 'CRVR-0131',
    name: 'Chiang Rai Mangrove Restore',
    status: 'verified',
    est_removal_tco2e: 18400,
    overlap: false,
    evidence_count: 4,
  },
  {
    ...base,
    id: 3,
    code: 'CRVR-0156',
    name: 'Phetchabun Agroforestry',
    status: 'draft',
    area_ha: null,
    submitted_at: null,
    overlap: false,
    evidence_count: 0,
  },
]

/**
 * Home loads the project list and, for developers, F3's change-request notes. Answer each request
 * with a fresh Response — one shared Response body can only be read once.
 */
function mockHome(projectsBody: unknown, notes: unknown[] = [], status = 200) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (input) =>
      String(input).endsWith('/verifications/notes')
        ? Response.json(notes)
        : Response.json(projectsBody, { status }),
    )
}

describe('HomePage', () => {
  it('shows a developer their projects, live status and what needs action', async () => {
    mockHome(projects)
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(await screen.findByText('2 registered · 2 waiting on you')).toBeInTheDocument()
    expect(screen.getByText('18,400')).toBeInTheDocument() // tCO₂e verified
    expect(screen.getByText('7')).toBeInTheDocument() // evidence files

    const rows = within(screen.getByRole('region', { name: 'Projects' })).getAllByRole('link', {
      name: /CRVR-/,
    })
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveTextContent('OVERLAP')
    expect(rows[0]).toHaveTextContent('1,240 ha · VM0047 · submitted 12 Sep')
    expect(rows[1]).toHaveTextContent('VERIFIED')
    expect(rows[2]).toHaveTextContent('DRAFT')
    // Drafts reopen the form; everything else opens the read-only page
    expect(rows[2]).toHaveAttribute('href', '/projects/3/edit')
    expect(rows[0]).toHaveAttribute('href', '/projects/1')
  })

  it('reserves the satellite-monitoring slot', async () => {
    mockHome(projects)
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    const slot = screen.getByRole('region', { name: 'Latest satellite check' })
    expect(within(slot).getByText('DEFERRED')).toBeInTheDocument()
  })

  it('gives registry staff the overview of every submission', async () => {
    mockHome(projects)
    renderWithProviders(<HomePage />, { user: makeUser('registry_staff') })

    expect(screen.getByRole('heading', { name: 'All projects' })).toBeInTheDocument()
    expect(await screen.findByText('2 submissions · 1 awaiting verification')).toBeInTheDocument()
    expect(screen.getByText('Overlap flagged')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /CRVR-/ })[2]).toHaveAttribute('href', '/projects/3')
  })

  it('invites a new developer to register', async () => {
    mockHome([])
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(
      await screen.findByRole('link', { name: 'Register your first project' }),
    ).toHaveAttribute('href', '/projects/new')
  })

  it('reports a failed load', async () => {
    mockHome({ detail: 'Database offline' }, [], 503)
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(await screen.findByRole('alert')).toHaveTextContent('Database offline')
  })

  it('shows a developer what was sent back: changes requested or rejected', async () => {
    mockHome(projects, [
      {
        project_id: 1,
        project_code: 'CRVR-0147',
        project_name: 'Nan Reforestation Phase II',
        kind: 'changes_requested',
        note: 'Upload the 2026 survey.',
        at: '2026-10-30T00:00:00Z',
      },
      {
        project_id: 2,
        project_code: 'CRVR-0131',
        project_name: 'Chiang Rai Mangrove Restore',
        kind: 'rejected',
        note: 'Land title does not match the applicant.',
        at: '2026-10-31T00:00:00Z',
      },
    ])
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(await screen.findByText('CRVR-0147 · changes requested')).toBeInTheDocument()
    expect(screen.getByText('Upload the 2026 survey.')).toBeInTheDocument()
    expect(screen.getByText('CRVR-0131 · verification rejected')).toBeInTheDocument()
    expect(screen.getByText('Land title does not match the applicant.')).toBeInTheDocument()
  })

  it('points verifiers to their queue without asking for projects', () => {
    const fetch = mockFetch()
    renderWithProviders(<HomePage />, { user: makeUser('verifier') })

    expect(screen.getByRole('link', { name: 'Open the verification queue' })).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })
})
