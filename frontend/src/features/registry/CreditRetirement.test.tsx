import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import type { User } from '@/auth/types'
import { makeUser, renderWithProviders } from '@/test/render'

import type { CreditDetail } from './api'
import { CreditPage } from './CreditPage'
import type { Holding, Holdings, Retirements } from './holdings-api'

// Omit keeps this fixture valid whether or not the detail still carries ledger_status (#29)
const credit: Omit<CreditDetail, 'ledger_status'> = {
  id: 7,
  serial: 'CRVR-0147-2026-A00000001-000000001-000008400',
  project_reference: 'CRVR-0147',
  project_name: 'Nan Reforestation Phase II',
  country: 'Thailand',
  methodology: 'VM0047',
  vintage: 2026,
  quantity: 8400,
  verification_status: 'approved',
  status: 'active',
  verifier_name: 'TUV Nord',
  verification_reference: 'VER-1',
  approval_reference: 'APP-1',
  signed_off_at: '2026-01-02T00:00:00Z',
  issued_at: '2026-02-02T00:00:00Z',
  history: [{ action: 'issued', occurred_at: '2026-02-02T00:00:00Z' }],
  monitoring: 'not_available',
}
const retirements: Retirements = {
  quantity: 8400,
  retired_quantity: 15,
  items: [
    {
      serial_block: 'CRVR-0147-2026-A00000001-000000001-000000015',
      quantity: 15,
      beneficiary: 'Nordic Airways',
      reason: '2026 Scope 1 offset',
      reporting_year: 2026,
      retired_at: '2026-11-17T00:00:00Z',
    },
  ],
}
const held: Holding = {
  id: 3,
  serial_block: 'CRVR-0147-2026-A00000001-000000016-000000040',
  first_unit: 16,
  last_unit: 40,
  quantity: 25,
  status: 'held',
  allocated_at: '2026-11-16T00:00:00Z',
  retired_at: null,
  beneficiary: null,
  reason: null,
  reporting_year: null,
  buyer_email: null,
}
const retired: Holding = {
  ...held,
  id: 2,
  serial_block: retirements.items[0].serial_block,
  first_unit: 1,
  last_unit: 15,
  quantity: 15,
  status: 'retired',
  retired_at: '2026-11-17T00:00:00Z',
  beneficiary: 'Nordic Airways',
  reason: '2026 Scope 1 offset',
  reporting_year: 2026,
}
const holdings: Holdings = {
  quantity: 8400,
  allocated: 40,
  unallocated: 8360,
  retired: 15,
  items: [retired, held],
}

function backend(posts: Record<string, Response> = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = String(input)
    if ((init?.method ?? 'GET') === 'POST') {
      if (path in posts) return posts[path].clone()
      throw new Error(`Unexpected POST ${path}`)
    }
    if (path === '/api/registry/credits/7') return Response.json(credit)
    if (path === '/api/registry/credits/7/retirements') return Response.json(retirements)
    if (path === '/api/registry/credits/7/holdings') return Response.json(holdings)
    throw new Error(`Unexpected request ${path}`)
  })
}

function renderCredit(user: User | null) {
  return renderWithProviders(
    <Routes>
      <Route path="/registry/:id" element={<CreditPage />} />
    </Routes>,
    { route: '/registry/7', user },
  )
}

describe('Credit retirement', () => {
  it('shows public retirement records without holdings to anonymous visitors', async () => {
    const fetch = backend()
    renderCredit(null)
    const section = await screen.findByRole('region', { name: 'Retirements' })
    expect(await within(section).findByText('Nordic Airways')).toBeInTheDocument()
    expect(section).toHaveTextContent('15 of 8,400 tCO₂e retired')
    expect(section).toHaveTextContent('2026 Scope 1 offset')
    expect(section).toHaveTextContent('reporting year 2026')
    expect(within(section).getByText(retirements.items[0].serial_block)).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Your credits' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalledWith('/api/registry/credits/7/holdings', expect.anything())
  })

  it('lets a buyer retire part of a held range after a permanence warning', async () => {
    const fetch = backend({
      '/api/registry/holdings/3/retire': Response.json({ retired: held, remaining: null }),
    })
    renderCredit(makeUser('buyer'))
    const section = await screen.findByRole('region', { name: 'Your credits' })
    expect(await within(section).findByText('Retired · locked')).toBeInTheDocument()
    // Only the held range can be retired
    expect(within(section).getAllByRole('button', { name: /Retire credits/ })).toHaveLength(1)
    await userEvent.click(
      within(section).getByRole('button', { name: `Retire credits ${held.serial_block}` }),
    )
    const dialog = await screen.findByRole('dialog', { name: 'Retire credits' })
    expect(dialog).toHaveTextContent('Retirement is permanent')
    expect(within(dialog).getByLabelText('Quantity (tCO₂e)')).toHaveValue(25)
    await userEvent.clear(within(dialog).getByLabelText('Quantity (tCO₂e)'))
    await userEvent.type(within(dialog).getByLabelText('Quantity (tCO₂e)'), '10')
    await userEvent.type(within(dialog).getByLabelText('Beneficiary'), 'Nordic Airways')
    await userEvent.type(within(dialog).getByLabelText('Retirement reason'), 'Scope 1 offset')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Retire permanently' }))
    expect(fetch).toHaveBeenCalledWith(
      '/api/registry/holdings/3/retire',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          quantity: 10,
          beneficiary: 'Nordic Airways',
          reason: 'Scope 1 offset',
          reporting_year: new Date().getFullYear(),
        }),
      }),
    )
    await vi.waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('keeps the dialog open and shows the reason when retirement is refused', async () => {
    backend({
      '/api/registry/holdings/3/retire': Response.json(
        { detail: 'These credits are already retired' },
        { status: 409 },
      ),
    })
    renderCredit(makeUser('buyer'))
    const section = await screen.findByRole('region', { name: 'Your credits' })
    await userEvent.click(
      await within(section).findByRole('button', { name: `Retire credits ${held.serial_block}` }),
    )
    const dialog = await screen.findByRole('dialog', { name: 'Retire credits' })
    await userEvent.type(within(dialog).getByLabelText('Beneficiary'), 'Nordic Airways')
    await userEvent.type(within(dialog).getByLabelText('Retirement reason'), 'Offset')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Retire permanently' }))
    expect(await within(dialog).findByText('These credits are already retired')).toBeInTheDocument()
  })

  it('lets registry staff see every holding and allocate to a buyer', async () => {
    const fetch = backend({
      '/api/registry/credits/7/holdings': Response.json(held, { status: 201 }),
    })
    renderCredit(makeUser('registry_staff'))
    const section = await screen.findByRole('region', { name: 'Holdings' })
    expect(await within(section).findByText('40 allocated · 8,360 unallocated')).toBeInTheDocument()
    expect(
      within(section).queryByRole('button', { name: /Retire credits/ }),
    ).not.toBeInTheDocument()
    const form = within(section).getByRole('form', { name: 'Allocate credits' })
    await userEvent.type(within(form).getByLabelText('Buyer email'), 'buyer@crvr.local')
    await userEvent.type(within(form).getByLabelText('Quantity (tCO₂e)'), '100')
    await userEvent.click(within(form).getByRole('button', { name: 'Allocate to buyer' }))
    expect(fetch).toHaveBeenCalledWith(
      '/api/registry/credits/7/holdings',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ buyer_email: 'buyer@crvr.local', quantity: 100 }),
      }),
    )
  })

  it('shows no holdings section to developers', async () => {
    backend()
    renderCredit(makeUser('developer'))
    await screen.findByRole('region', { name: 'Retirements' })
    expect(screen.queryByRole('region', { name: 'Holdings' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Your credits' })).not.toBeInTheDocument()
  })
})
