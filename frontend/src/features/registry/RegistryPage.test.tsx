import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import type { CreditDetail, CreditPage } from './api'
import { RegistryPage } from './RegistryPage'

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
const page: CreditPage = { items: [credit], total: 1, page: 1, page_size: 20 }

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
  await userEvent.click(await screen.findByRole('button', { name: /Nan Reforestation/ }))
  return screen.findByRole('region', { name: 'Credit traceability' })
}

describe('Public registry', () => {
  it('shows public results and full traceability with deferred states', async () => {
    responses()
    renderWithProviders(<RegistryPage />)
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

  it('submits literal search text, resets selection and shows no matches', async () => {
    const fetch = responses({
      '/api/registry/credits?q=no+match&page=1': { ...page, items: [], total: 0 },
    })
    renderWithProviders(<RegistryPage />)
    await selectCredit()
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Search project, serial or country' }),
      'no match',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('No matching credits')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Credit traceability' })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      '/api/registry/credits?q=no+match&page=1',
      expect.any(Object),
    )
  })

  it('explains an empty registry', async () => {
    responses({ '/api/registry/credits?q=&page=1': { ...page, items: [], total: 0 } })
    renderWithProviders(<RegistryPage />)
    expect(await screen.findByText('No issued credits available')).toBeInTheDocument()
  })

  it('offers retry on a list error', async () => {
    const fetch = responses({
      '/api/registry/credits?q=&page=1': Response.json(
        { detail: 'Registry unavailable' },
        { status: 503 },
      ),
    })
    renderWithProviders(<RegistryPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Registry unavailable')
    fetch.mockResolvedValue(Response.json(page))
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('button', { name: /Nan Reforestation/ })).toBeInTheDocument()
  })

  it('allows an authorised buyer to request reviewed evidence', async () => {
    responses({
      '/api/registry/credits/7/evidence': {
        serial: credit.serial,
        notice: 'Reviewed summaries only',
        items: [{ id: 1, title: 'Verification report', summary: 'Reviewed project evidence' }],
      },
    })
    renderWithProviders(<RegistryPage />, { user: makeUser('buyer') })
    expect(screen.getByText('Showing projects you are permitted to access.')).toBeInTheDocument()
    const panel = await selectCredit()
    await userEvent.click(await within(panel).findByRole('button', { name: 'Evidence pack' }))
    expect(await screen.findByText('Reviewed project evidence')).toBeInTheDocument()
    expect(screen.getByText('Reviewed summaries only')).toBeInTheDocument()
  })

  it('handles empty evidence and denied evidence without exposing data', async () => {
    const fetch = responses({
      '/api/registry/credits/7/evidence': { serial: credit.serial, notice: '', items: [] },
    })
    renderWithProviders(<RegistryPage />, { user: makeUser('buyer') })
    const panel = await selectCredit()
    const button = await within(panel).findByRole('button', { name: 'Evidence pack' })
    await userEvent.click(button)
    expect(await screen.findByText('No permitted evidence')).toBeInTheDocument()
    fetch.mockResolvedValue(Response.json({ detail: 'Credit not found' }, { status: 404 }))
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('Credit not found')
  })

  it('disables evidence for a developer', async () => {
    responses()
    renderWithProviders(<RegistryPage />, { user: makeUser('developer') })
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
      renderWithProviders(<RegistryPage />)
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

  it('paginates and clears the previous traceability panel', async () => {
    responses({
      '/api/registry/credits?q=&page=1': { ...page, total: 21 },
      '/api/registry/credits?q=&page=2': {
        ...page,
        page: 2,
        total: 21,
        items: [{ ...credit, id: 8, project_name: 'Second page project' }],
      },
    })
    renderWithProviders(<RegistryPage />)
    await selectCredit()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('button', { name: /Second page project/ })).toBeInTheDocument()
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(screen.queryByRole('region', { name: 'Credit traceability' })).not.toBeInTheDocument()
  })

  it('shows a loading state before the request resolves', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<RegistryPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading credits')
  })

  it('handles missing traceability', async () => {
    responses({
      '/api/registry/credits/7': Response.json({ detail: 'Credit not found' }, { status: 404 }),
    })
    renderWithProviders(<RegistryPage />)
    await userEvent.click(await screen.findByRole('button', { name: /Nan Reforestation/ }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Credit not found'))
  })
})
