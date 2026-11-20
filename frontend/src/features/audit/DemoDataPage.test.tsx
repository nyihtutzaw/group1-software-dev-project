import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import type { DemoData } from './demo-data-api'
import { DemoDataPage } from './DemoDataPage'

const FULL: DemoData = {
  enabled: true,
  counts: { users: 6, projects: 5, boundaries: 4, credits: 3, ledger_entries: 41 },
}
const LIVE: DemoData = {
  enabled: true,
  counts: { users: 6, projects: 1, boundaries: 1, credits: 0, ledger_entries: 2 },
}

function mockApi(demo: DemoData) {
  const reset = vi.fn<(init?: RequestInit) => DemoData>(() => LIVE)
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const key = `${init?.method ?? 'GET'} ${String(input)}`
    if (key === 'GET /api/admin/demo-data') return Response.json(demo)
    if (key === 'POST /api/admin/demo-data/reset') return Response.json(reset(init))
    return Response.json([])
  })
  return reset
}

describe('DemoDataPage', () => {
  it('shows what the server holds and both starting points', async () => {
    mockApi(FULL)
    renderWithProviders(<DemoDataPage />, { user: makeUser('admin') })

    expect(await screen.findByText('41')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reset to live demo start' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Reset to full sample data' })).toBeEnabled()
  })

  it('resets only after RESET is typed', async () => {
    const reset = mockApi(FULL)
    renderWithProviders(<DemoDataPage />, { user: makeUser('admin') })

    await userEvent.click(await screen.findByRole('button', { name: 'Reset to live demo start' }))
    const wipe = screen.getByRole('button', { name: 'Wipe and reset' })
    expect(wipe).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Type RESET to confirm'), 'RESET')
    await userEvent.click(wipe)

    expect(await screen.findByText('Demo data reset')).toBeInTheDocument()
    expect(reset).toHaveBeenCalledWith(
      expect.objectContaining({ body: JSON.stringify({ start: 'live', confirm: 'RESET' }) }),
    )
  })

  it('explains that a server outside demo mode cannot be reset', async () => {
    mockApi({ ...FULL, enabled: false })
    renderWithProviders(<DemoDataPage />, { user: makeUser('admin') })

    expect(await screen.findByText('Reset is off on this server')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reset to live demo start' })).toBeDisabled()
  })
})
