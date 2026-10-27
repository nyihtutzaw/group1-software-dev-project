import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { BoundaryPage } from './BoundaryPage'
import type { BoundaryCheck, Geometry, OverlapFlag, ProjectBoundary } from './types'

// Leaflet needs a real browser layout; stand in a map that can "draw" a shape.
const DRAWN: Geometry = {
  type: 'Polygon',
  coordinates: [
    [
      [100.7, 18.7],
      [100.71, 18.7],
      [100.71, 18.71],
      [100.7, 18.7],
    ],
  ],
}
vi.mock('./BoundaryMap', () => ({
  BoundaryMap: ({ onChange, editable }: { onChange: (g: Geometry) => void; editable: boolean }) => (
    <div aria-label="Boundary map">
      {editable && (
        <button type="button" onClick={() => onChange(DRAWN)}>
          simulate drawing
        </button>
      )}
    </div>
  ),
}))

const PROJECTS = [
  { id: 4, code: 'CRVR-0147', name: 'Nan Reforestation Phase II', status: 'submitted' },
  { id: 5, code: 'CRVR-0156', name: 'Phetchabun Agroforestry', status: 'draft' },
]

const OVERLAP_CHECK: BoundaryCheck = {
  area_m2: 12_400_000,
  area_ha: 1240,
  vertices: 6,
  checked_against: 3,
  tolerance_pct: 0.5,
  blocked: true,
  overlaps: [
    {
      project_id: 2,
      project_code: 'CRVR-0092',
      project_name: 'Phrae Agroforestry',
      registered_at: '2026-03-03T00:00:00Z',
      overlap_m2: 384_000,
      overlap_ha: 38.4,
      overlap_pct: 3.1,
      exceeds_tolerance: true,
      intersection: DRAWN,
    },
  ],
}

const CLEAR_CHECK: BoundaryCheck = { ...OVERLAP_CHECK, blocked: false, overlaps: [], area_ha: 120 }

function flag(status: OverlapFlag['status']): OverlapFlag {
  return {
    id: 7,
    other_project_id: 2,
    other_project_code: 'CRVR-0092',
    other_project_name: 'Phrae Agroforestry',
    overlap_ha: 38.4,
    overlap_pct: 3.1,
    status,
    dispute_reason: null,
    resolution_note: status === 'resolved' ? 'Site visit confirmed the river line.' : null,
    created_at: '2026-10-27T00:00:00Z',
    resolved_at: null,
  }
}

function saved(overrides: Partial<ProjectBoundary> = {}): ProjectBoundary {
  return {
    project_id: 4,
    project_code: 'CRVR-0147',
    project_name: 'Nan Reforestation Phase II',
    geometry: DRAWN,
    source: 'drawn',
    updated_at: '2026-10-27T00:00:00Z',
    check: OVERLAP_CHECK,
    flags: [flag('open')],
    issuance_blocked: 'The boundary overlaps another project and has not been resolved.',
    can_edit: true,
    ...overrides,
  }
}

const COLLECTION = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: DRAWN,
      properties: {
        project_id: 4,
        code: 'CRVR-0147',
        name: PROJECTS[0].name,
        area_ha: 1240,
        flagged: true,
      },
    },
  ],
}

type Route = unknown | ((init?: RequestInit) => unknown)

/** Answer fetch() by "METHOD /path" (without /api); anything else is a 404. */
function mockApi(routes: Record<string, Route>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = String(input).replace(/^\/api/, '')
    const route = routes[`${init?.method ?? 'GET'} ${path}`]
    if (route === undefined) return Response.json({ detail: 'Not found' }, { status: 404 })
    return Response.json(typeof route === 'function' ? route(init) : route)
  })
}

describe('BoundaryPage', () => {
  it('shows the developer their overlap, with the actions from the mock-up', async () => {
    mockApi({
      'GET /projects': PROJECTS,
      'GET /boundaries': COLLECTION,
      'GET /boundaries/4': saved(),
    })
    renderWithProviders(<BoundaryPage />, {
      route: '/boundary?project=4',
      user: makeUser('developer'),
    })

    expect(await screen.findByText('Overlap found — 38.4 ha')).toBeInTheDocument()
    expect(screen.getByText(/Your boundary overlaps/)).toBeInTheDocument()
    expect(screen.getByText('CRVR-0092 (Phrae Agroforestry)')).toBeInTheDocument()
    expect(screen.getByText(/registered 3 Mar 2026. That is 3.1% of your area/)).toBeInTheDocument()
    expect(screen.getByText('Nan Reforestation Phase II · 1,240.0 ha · WGS 84')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Re-draw boundary' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dispute overlap' })).toBeInTheDocument()
    expect(screen.getByText(/Credit issuance is blocked/)).toBeInTheDocument()
  })

  it('gives verifiers a read-only view', async () => {
    mockApi({
      'GET /boundaries': COLLECTION,
      'GET /boundaries/4': saved({ can_edit: false }),
    })
    renderWithProviders(<BoundaryPage />, { route: '/boundary', user: makeUser('verifier') })

    expect(await screen.findByText(/This boundary overlaps/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Re-draw boundary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dispute overlap' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resolve overlap' })).not.toBeInTheDocument()
  })

  it('checks a newly drawn boundary and saves it', async () => {
    const save = vi.fn(() =>
      saved({ project_id: 5, check: CLEAR_CHECK, flags: [], issuance_blocked: null }),
    )
    const api = mockApi({
      'GET /projects': PROJECTS,
      'GET /boundaries': COLLECTION,
      'POST /boundaries/check': CLEAR_CHECK,
      'PUT /boundaries/5': save,
    })
    renderWithProviders(<BoundaryPage />, {
      route: '/boundary?project=5',
      user: makeUser('developer'),
    })

    expect(await screen.findByText('Phetchabun Agroforestry · no boundary yet')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'simulate drawing' }))

    expect(await screen.findByText('Boundary drawn — no overlap')).toBeInTheDocument()
    expect(api).toHaveBeenCalledWith(
      '/api/boundaries/check',
      expect.objectContaining({ body: JSON.stringify({ geometry: DRAWN, project_id: 5 }) }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Save boundary' }))
    expect(save).toHaveBeenCalledWith(
      expect.objectContaining({ body: JSON.stringify({ geometry: DRAWN, source: 'drawn' }) }),
    )
  })

  it('lets registry staff resolve an open flag', async () => {
    const resolve = vi.fn(() => flag('resolved'))
    mockApi({
      'GET /projects': PROJECTS,
      'GET /boundaries': COLLECTION,
      'GET /boundaries/4': saved({ can_edit: false }),
      'POST /boundaries/flags/7/resolve': resolve,
    })
    renderWithProviders(<BoundaryPage />, {
      route: '/boundary?project=4',
      user: makeUser('registry_staff'),
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Resolve overlap' }))
    await userEvent.type(screen.getByLabelText('Resolution note'), 'Site visit confirmed it.')
    await userEvent.click(screen.getByRole('button', { name: 'Resolve' }))

    expect(resolve).toHaveBeenCalledWith(
      expect.objectContaining({ body: JSON.stringify({ note: 'Site visit confirmed it.' }) }),
    )
  })

  it('shows a staff-resolved overlap as cleared, not blocking', async () => {
    mockApi({
      'GET /projects': PROJECTS,
      'GET /boundaries': COLLECTION,
      'GET /boundaries/4': saved({ flags: [flag('resolved')], issuance_blocked: null }),
    })
    renderWithProviders(<BoundaryPage />, {
      route: '/boundary?project=4',
      user: makeUser('developer'),
    })

    expect(await screen.findByText('Overlap resolved by registry staff')).toBeInTheDocument()
    expect(screen.queryByText(/Overlap found/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Credit issuance is blocked/)).not.toBeInTheDocument()
  })
})
