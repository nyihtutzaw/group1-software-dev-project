import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { LedgerPage } from './LedgerPage'

const ENTRY = {
  id: 1,
  created_at: '2026-11-14T16:00:00Z',
  action: 'boundary.saved',
  actor_id: 2,
  actor_email: 'dev@example.com',
  actor_role: 'developer',
  entity: 'boundary',
  entity_id: 42,
  payload: { area_m2: 12_400_000 },
  prev_hash: '0'.repeat(64),
  hash: 'a'.repeat(64),
}

const PAGE = { total: 1, page: 1, page_size: 50, items: [ENTRY] }

describe('LedgerPage', () => {
  it('shows entries and integrity status for a buyer', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json(PAGE))
      .mockResolvedValueOnce(Response.json({ valid: true, error: null }))

    renderWithProviders(<LedgerPage />, { user: makeUser('buyer') })

    expect(await screen.findByText('Boundary — Saved')).toBeInTheDocument()
    expect(screen.getByText(/dev@example\.com · Developer/)).toBeInTheDocument()
    expect(await screen.findByText(/chain intact/i)).toBeInTheDocument()
  })

  it('shows chain-intact alert for registry_staff', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json(PAGE)) // ledger entries
      .mockResolvedValueOnce(Response.json({ valid: true, error: null })) // verify

    renderWithProviders(<LedgerPage />, { user: makeUser('registry_staff') })

    expect(await screen.findByText(/chain intact/i)).toBeInTheDocument()
  })

  it('shows broken-chain alert when verify reports invalid', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json(PAGE))
      .mockResolvedValueOnce(Response.json({ valid: false, error: 'Hash mismatch at entry id=1' }))

    renderWithProviders(<LedgerPage />, { user: makeUser('admin') })

    expect(await screen.findByText(/chain integrity broken/i)).toBeInTheDocument()
    expect(await screen.findByText(/Hash mismatch at entry id=1/)).toBeInTheDocument()
  })

  it('shows short hash and details toggle for entries with payload', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json(PAGE))
      .mockResolvedValueOnce(Response.json({ valid: true, error: null }))

    const user = userEvent.setup()
    renderWithProviders(<LedgerPage />, { user: makeUser('verifier') })

    // Hash pill
    expect(await screen.findByText(`sha256 aaaa…aaaa`)).toBeInTheDocument()

    // Expand payload details
    const toggle = screen.getByText('Details')
    await user.click(toggle)
    expect(screen.getByText(/12400000/)).toBeInTheDocument()
  })

  it('shows empty state when there are no entries', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json({ total: 0, page: 1, page_size: 50, items: [] }))
      .mockResolvedValueOnce(Response.json({ valid: true, error: null }))

    renderWithProviders(<LedgerPage />, { user: makeUser('verifier') })

    expect(await screen.findByText('No entries yet')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'))

    renderWithProviders(<LedgerPage />, { user: makeUser('admin') })

    expect(await screen.findByText('Could not load ledger')).toBeInTheDocument()
  })

  it('shows pagination controls when total exceeds page size', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json({ total: 120, page: 1, page_size: 50, items: [ENTRY] }))
      .mockResolvedValueOnce(Response.json({ valid: true, error: null }))
      .mockResolvedValueOnce(
        Response.json({
          total: 120,
          page: 2,
          page_size: 50,
          items: [{ ...ENTRY, id: 51, entity_id: 51 }],
        }),
      )

    const user = userEvent.setup()
    renderWithProviders(<LedgerPage />, { user: makeUser('buyer') })

    expect(await screen.findByText(/page 1 of 3/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText(/page 2 of 3/i)).toBeInTheDocument()
  })

  it('does not request integrity verification for roles without access', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(PAGE))
    renderWithProviders(<LedgerPage />, { user: makeUser('developer') })

    expect(await screen.findByText('Boundary — Saved')).toBeInTheDocument()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })
})
