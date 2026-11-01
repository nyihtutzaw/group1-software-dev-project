import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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

describe('HomePage', () => {
  it('shows a developer their projects, live status and what needs action', async () => {
    mockFetch(projects)
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(await screen.findByText('2 registered · 2 waiting on you')).toBeInTheDocument()
    expect(screen.getByText('18,400')).toBeInTheDocument() // tCO₂e verified
    expect(screen.getByText('7')).toBeInTheDocument() // evidence files

    const rows = within(screen.getByRole('region', { name: 'Projects' })).getAllByRole('link', {
      name: /CRVR-/,
    })
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveTextContent('OVERLAP')
    expect(rows[0]).toHaveTextContent('1,240 ha · VM0047 · submitted 12 Sept')
    expect(rows[1]).toHaveTextContent('VERIFIED')
    expect(rows[2]).toHaveTextContent('DRAFT')
    // Drafts reopen the form; everything else opens the read-only page
    expect(rows[2]).toHaveAttribute('href', '/projects/3/edit')
    expect(rows[0]).toHaveAttribute('href', '/projects/1')
  })

  it('reserves the satellite-monitoring slot', async () => {
    mockFetch(projects)
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    const slot = screen.getByRole('region', { name: 'Latest satellite check' })
    expect(within(slot).getByText('DEFERRED')).toBeInTheDocument()
  })

  it('gives registry staff the overview of every submission', async () => {
    mockFetch(projects)
    renderWithProviders(<HomePage />, { user: makeUser('registry_staff') })

    expect(screen.getByRole('heading', { name: 'All projects' })).toBeInTheDocument()
    expect(await screen.findByText('2 submissions · 1 awaiting verification')).toBeInTheDocument()
    expect(screen.getByText('Overlap flagged')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /CRVR-/ })[2]).toHaveAttribute('href', '/projects/3')
  })

  it('invites a new developer to register', async () => {
    mockFetch([])
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(
      await screen.findByRole('link', { name: 'Register your first project' }),
    ).toHaveAttribute('href', '/projects/new')
  })

  it('reports a failed load', async () => {
    mockFetch().mockResolvedValue(Response.json({ detail: 'Database offline' }, { status: 503 }))
    renderWithProviders(<HomePage />, { user: makeUser('developer') })

    expect(await screen.findByRole('alert')).toHaveTextContent('Database offline')
  })

  it('points verifiers to their queue without asking for projects', () => {
    const fetch = mockFetch()
    renderWithProviders(<HomePage />, { user: makeUser('verifier') })

    expect(screen.getByRole('link', { name: 'Open the verification queue' })).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })
})
