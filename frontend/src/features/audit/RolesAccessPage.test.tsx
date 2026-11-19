import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, mockFetch, renderWithProviders } from '@/test/render'

import type { AccessMatrix } from './access-api'
import { RolesAccessPage } from './RolesAccessPage'

const ALL = ['developer', 'verifier', 'registry_staff', 'buyer', 'admin'] as const

const MATRIX: AccessMatrix = {
  roles: [...ALL],
  endpoints: [
    {
      method: 'POST',
      path: '/api/auth/login',
      summary: 'Login',
      area: 'auth',
      access: 'public',
      roles: [...ALL],
    },
    {
      method: 'GET',
      path: '/api/ledger',
      summary: 'Return one page of audit ledger entries, newest first',
      area: 'F5 audit',
      access: 'roles',
      roles: ['verifier', 'registry_staff', 'buyer', 'admin'],
    },
  ],
}

/** The cells of a table row, as their screen-reader text, skipping the row header. */
function cells(table: HTMLElement, rowName: RegExp) {
  const row = within(table).getByRole('row', { name: rowName })
  return within(row)
    .getAllByRole('cell')
    .map((cell) => cell.querySelector('.sr-only')?.textContent)
}

describe('RolesAccessPage', () => {
  it('shows the role, page and API access matrices', async () => {
    mockFetch(MATRIX)
    renderWithProviders(<RolesAccessPage />, { user: makeUser('admin') })

    const roles = screen.getByRole('table', { name: 'Roles' })
    expect(within(roles).getByText('Registry staff')).toBeInTheDocument()
    expect(within(roles).getAllByRole('row')).toHaveLength(6)

    const pages = screen.getByRole('table', { name: 'Page access' })
    // Signed out, developer, verifier, registry staff, buyer, admin
    expect(cells(pages, /^System › Role & Access/)).toEqual([
      'No access',
      'No access',
      'No access',
      'No access',
      'No access',
      'Allowed',
    ])
    expect(cells(pages, /^Registry/)[0]).toBe('Allowed')

    const api = await screen.findByRole('table', { name: 'API access' })
    expect(within(api).getByText('F5 audit')).toBeInTheDocument()
    expect(cells(api, /\/api\/ledger/)).toEqual([
      'No access',
      'Allowed',
      'Allowed',
      'Allowed',
      'Allowed',
    ])
    expect(within(api).getByText('Public')).toBeInTheDocument()
  })

  it('is read-only: no inputs or buttons to change access', async () => {
    mockFetch(MATRIX)
    renderWithProviders(<RolesAccessPage />, { user: makeUser('admin') })

    await screen.findByRole('table', { name: 'API access' })
    expect(screen.getByText('Read-only')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('says so when the API matrix cannot be loaded', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      Response.json({ detail: 'Your role cannot do this' }, { status: 403 }),
    )
    renderWithProviders(<RolesAccessPage />, { user: makeUser('admin') })

    expect(await screen.findByText('Could not load the API access matrix')).toBeInTheDocument()
    // The page matrix does not depend on the server
    expect(screen.getByRole('table', { name: 'Page access' })).toBeInTheDocument()
  })
})
