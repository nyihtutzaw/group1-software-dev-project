import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { BottomNav } from './BottomNav'
import { navFor } from './nav'
import { Sidebar } from './Sidebar'

describe('Sidebar System menu', () => {
  it('starts closed elsewhere and opens to show its child pages', async () => {
    const user = makeUser('admin')
    renderWithProviders(<Sidebar items={navFor('admin')} user={user} />, { route: '/ledger' })

    const system = screen.getByRole('button', { name: 'System' })
    expect(system).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('link', { name: 'Role & Access' })).not.toBeInTheDocument()

    await userEvent.click(system)

    expect(system).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('link', { name: 'Role & Access' })).toHaveAttribute(
      'href',
      '/system/roles-access',
    )
  })

  it('is open on one of its pages, with that page marked current', () => {
    renderWithProviders(<Sidebar items={navFor('admin')} user={makeUser('admin')} />, {
      route: '/system/roles-access',
    })

    expect(screen.getByRole('button', { name: 'System' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('link', { name: 'Role & Access' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('is not shown to other roles', () => {
    renderWithProviders(<Sidebar items={navFor('registry_staff')} user={null} />)
    expect(screen.queryByRole('button', { name: 'System' })).not.toBeInTheDocument()
  })
})

describe('BottomNav System tab', () => {
  it('is one tab that opens the first System page', () => {
    renderWithProviders(<BottomNav items={navFor('admin')} />, { route: '/ledger' })

    expect(screen.getByRole('link', { name: 'System' })).toHaveAttribute(
      'href',
      '/system/roles-access',
    )
    expect(screen.queryByRole('link', { name: 'Role & Access' })).not.toBeInTheDocument()
  })
})
