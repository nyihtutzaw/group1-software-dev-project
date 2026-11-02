import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import type { User } from '@/auth/types'
import { makeUser, renderWithProviders } from '@/test/render'

import type { CreditDetail, CreditPage as CreditPageData } from './api'
import { CreditPage } from './CreditPage'
import { RegistryPage } from './RegistryPage'

function renderRegistry(user: User | null = null, route = '/registry') {
  return renderWithProviders(
    <Routes>
      <Route path="/registry" element={<RegistryPage />} />
      <Route path="/registry/:id" element={<CreditPage />} />
    </Routes>,
    { route, user },
  )
}

const credit: CreditDetail = {
  id: 7,
  serial: 'TH-0147-2026-A-00001-08400',
  project_reference: 'CRVR-0147',
  project_name: 'Nan Reforestation Phase II',
  country: 'Thailand',
  methodology: 'Afforestation',
  vintage: 2026,
  quantity: 8400,
  verification_status: 'approved',
  status: 'active',
  verifier_name: 'TUV Nord (VVB-114)',
  verification_reference: 'VER-0147',
  approval_reference: 'APP-0147',
  signed_off_at: '2026-01-02T00:00:00Z',
  issued_at: '2026-02-02T00:00:00Z',
  history: [{ action: 'issued', occurred_at: '2026-02-02T00:00:00Z' }],
  monitoring: 'not_available',
  ledger_status: 'not_available',
}
const page: CreditPageData = { items: [credit], total: 1, page: 1, page_size: 20 }

function responses(overrides: Record<string, unknown> = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const path = String(input)
    if (path in overrides) {
      const body = overrides[path]
      return body instanceof Response ? body.clone() : Response.json(body)
    }
    if (path.startsWith('/api/registry/credits?')) return Response.json(page)
    if (path === '/api/registry/credits/7') return Response.json(credit)
    throw new Error(`Unexpected request ${path}`)
  })
}

async function selectCredit() {
  await userEvent.click(await screen.findByRole('link', { name: /Nan Reforestation/ }))
  return screen.findByRole('region', { name: 'Credit traceability' })
}

describe('Public registry', () => {
  it('shows public results and full traceability with deferred states', async () => {
    responses()
    renderRegistry()
    const panel = await selectCredit()
    expect(await within(panel).findByText('TUV Nord (VVB-114)')).toBeInTheDocument()
    expect(within(panel).getByText('Not available — monitoring is deferred')).toBeInTheDocument()
    expect(within(panel).getByText('Not available — ledger not connected')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Evidence pack' })).toBeDisabled()
    expect(
      within(panel).getByRole('link', { name: 'Sign in as an authorised buyer' }),
    ).toHaveAttribute('href', '/login')
    expect(within(panel).getByText('Issued')).toBeInTheDocument()
  })

  it('submits literal search text and shows no matches', async () => {
    const fetch = responses({
      '/api/registry/credits?q=no+match&page=1': { ...page, items: [], total: 0 },
    })
    renderRegistry()
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Search project, serial or country' }),
      'no match',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('No matching credits')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      '/api/registry/credits?q=no+match&page=1',
      expect.any(Object),
    )
  })

  it('explains an empty registry', async () => {
    responses({ '/api/registry/credits?q=&page=1': { ...page, items: [], total: 0 } })
    renderRegistry()
    expect(await screen.findByText('No issued credits available')).toBeInTheDocument()
  })

  it('offers retry on a list error', async () => {
    const fetch = responses({
      '/api/registry/credits?q=&page=1': Response.json(
        { detail: 'Registry unavailable' },
        { status: 503 },
      ),
    })
    renderRegistry()
    expect(await screen.findByRole('alert')).toHaveTextContent('Registry unavailable')
    fetch.mockResolvedValue(Response.json(page))
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: /Nan Reforestation/ })).toBeInTheDocument()
  })

  it('allows an authorised buyer to request reviewed evidence', async () => {
    responses({
      '/api/registry/credits/7/evidence': {
        serial: credit.serial,
        notice: 'Reviewed summaries only',
        items: [{ id: 1, title: 'Verification report', summary: 'Reviewed project evidence' }],
      },
    })
    renderRegistry(makeUser('buyer'))
    expect(screen.getByText('Showing projects you are permitted to access.')).toBeInTheDocument()
    const panel = await selectCredit()
    await userEvent.click(await within(panel).findByRole('button', { name: 'Evidence pack' }))
    const dialog = await screen.findByRole('dialog', { name: 'Evidence pack' })
    expect(within(dialog).getByText('Reviewed project evidence')).toBeInTheDocument()
    expect(within(dialog).getByText('Reviewed summaries only')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('handles empty evidence and denied evidence without exposing data', async () => {
    const fetch = responses({
      '/api/registry/credits/7/evidence': { serial: credit.serial, notice: '', items: [] },
    })
    renderRegistry(makeUser('buyer'))
    const panel = await selectCredit()
    const button = await within(panel).findByRole('button', { name: 'Evidence pack' })
    await userEvent.click(button)
    expect(await screen.findByText('No permitted evidence')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Close' }))
    fetch.mockResolvedValue(Response.json({ detail: 'Credit not found' }, { status: 404 }))
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('Credit not found')
  })

  it('disables evidence for a developer', async () => {
    responses()
    renderRegistry(makeUser('developer'))
    const panel = await selectCredit()
    expect(await within(panel).findByRole('button', { name: 'Evidence pack' })).toBeDisabled()
  })

  it.each([true, false])(
    'reports snapshot integrity %s without claiming ledger verification',
    async (matches) => {
      responses({
        '/api/registry/credits/7/integrity': {
          snapshot_matches: matches,
          ledger_status: 'not_available',
          notice: 'Independent ledger verification is not available.',
        },
      })
      renderRegistry()
      const panel = await selectCredit()
      await userEvent.click(
        await within(panel).findByRole('button', { name: 'Verify authenticity' }),
      )
      expect(
        await screen.findByText(
          matches ? 'Publication snapshot matches' : 'Publication snapshot mismatch',
        ),
      ).toBeInTheDocument()
      expect(
        screen.getByText('Independent ledger verification is not available.'),
      ).toBeInTheDocument()
    },
  )

  it('paginates through the results', async () => {
    responses({
      '/api/registry/credits?q=&page=1': { ...page, total: 21 },
      '/api/registry/credits?q=&page=2': {
        ...page,
        page: 2,
        total: 21,
        items: [{ ...credit, id: 8, project_name: 'Second page project' }],
      },
    })
    renderRegistry()
    await userEvent.click(await screen.findByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('link', { name: /Second page project/ })).toBeInTheDocument()
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(screen.getByRole('link', { name: /Second page project/ })).toHaveAttribute(
      'href',
      '/registry/8',
    )
  })

  it('shows a loading state before the request resolves', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))
    renderRegistry()
    expect(screen.getByRole('status')).toHaveTextContent('Loading credits')
  })

  it('handles missing traceability', async () => {
    responses({
      '/api/registry/credits/7': Response.json({ detail: 'Credit not found' }, { status: 404 }),
    })
    renderRegistry(null, '/registry/7')
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Credit not found'))
  })

  it('goes back to the same search results from a credit', async () => {
    responses({ '/api/registry/credits?q=nan&page=1': page })
    renderRegistry(null, '/registry?q=nan')
    await selectCredit()
    expect(screen.getByRole('link', { name: 'Public registry' })).toHaveAttribute(
      'href',
      '/registry?q=nan',
    )
  })
})
