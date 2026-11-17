import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import type { AccessGrant, AccessOptions } from './access-api'
import { AccessPage } from './AccessPage'

const options: AccessOptions = {
  buyers: [{ id: 5, full_name: 'Siam Airways', email: 'buyer@crvr.local', organization: null }],
  projects: [{ project_reference: 'CRVR-0147', project_name: 'Nan Reforestation Phase II' }],
}
const grant: AccessGrant = {
  project_reference: 'CRVR-0147',
  project_name: 'Nan Reforestation Phase II',
  buyer_id: 5,
  buyer_name: 'Siam Airways',
  buyer_email: 'buyer@crvr.local',
  buyer_organization: null,
  buyer_active: true,
}

/** A tiny fake backend that keeps grants in memory. */
function backend(initial: AccessGrant[] = []) {
  let grants = [...initial]
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = String(input)
    const method = init?.method ?? 'GET'
    if (path === '/api/registry/access/options') return Response.json(options)
    if (path === '/api/registry/access' && method === 'GET') return Response.json(grants)
    if (path === '/api/registry/access' && method === 'POST') {
      const body = JSON.parse(String(init?.body)) as { buyer_id: number }
      if (grants.length) {
        return Response.json({ detail: 'This buyer already has access' }, { status: 409 })
      }
      expect(body).toEqual({ project_reference: 'CRVR-0147', buyer_id: 5 })
      grants = [grant]
      return Response.json(grant, { status: 201 })
    }
    if (path === '/api/registry/access/CRVR-0147/5' && method === 'DELETE') {
      grants = []
      return new Response(null, { status: 204 })
    }
    throw new Error(`Unexpected ${method} ${path}`)
  })
}

describe('AccessPage', () => {
  it('grants a buyer access to a project', async () => {
    backend()
    renderWithProviders(<AccessPage />, { user: makeUser('registry_staff') })
    expect(await screen.findByText('No buyer access granted')).toBeInTheDocument()
    await screen.findByRole('option', { name: 'Nan Reforestation Phase II (CRVR-0147)' })
    await userEvent.selectOptions(
      screen.getByLabelText('Project'),
      'Nan Reforestation Phase II (CRVR-0147)',
    )
    await userEvent.selectOptions(screen.getByLabelText('Buyer'), 'Siam Airways · buyer@crvr.local')
    await userEvent.click(screen.getByRole('button', { name: 'Grant access' }))
    expect(await screen.findByText('Access granted')).toBeInTheDocument()
    const list = await screen.findByRole('region', { name: 'Current access' })
    expect(await within(list).findByText('buyer@crvr.local', { exact: false })).toBeInTheDocument()
    expect(within(list).getByText('CRVR-0147')).toBeInTheDocument()
  })

  it('shows the API error when a grant is refused', async () => {
    backend([grant])
    renderWithProviders(<AccessPage />, { user: makeUser('admin') })
    await screen.findByRole('option', { name: 'Nan Reforestation Phase II (CRVR-0147)' })
    await userEvent.selectOptions(
      screen.getByLabelText('Project'),
      'Nan Reforestation Phase II (CRVR-0147)',
    )
    await userEvent.selectOptions(screen.getByLabelText('Buyer'), 'Siam Airways · buyer@crvr.local')
    await userEvent.click(screen.getByRole('button', { name: 'Grant access' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This buyer already has access')
  })

  it('revokes access after confirmation', async () => {
    const fetch = backend([grant])
    renderWithProviders(<AccessPage />, { user: makeUser('registry_staff') })
    await userEvent.click(
      await screen.findByRole('button', { name: 'Revoke buyer@crvr.local from CRVR-0147' }),
    )
    const dialog = await screen.findByRole('dialog', { name: 'Revoke access?' })
    expect(dialog).toHaveTextContent('Siam Airways will no longer see Nan Reforestation Phase II')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Revoke access' }))
    expect(await screen.findByText('No buyer access granted')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      '/api/registry/access/CRVR-0147/5',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('explains when there is nothing to grant', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) =>
      String(input).endsWith('/options')
        ? Response.json({ buyers: [], projects: [] })
        : Response.json([]),
    )
    renderWithProviders(<AccessPage />, { user: makeUser('registry_staff') })
    expect(await screen.findByText('Nothing to grant yet')).toBeInTheDocument()
  })

  it('offers retry when grants fail to load', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) =>
      String(input).endsWith('/options')
        ? Response.json(options)
        : Response.json({ detail: 'Registry unavailable' }, { status: 503 }),
    )
    renderWithProviders(<AccessPage />, { user: makeUser('registry_staff') })
    expect(await screen.findByText('Registry unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
