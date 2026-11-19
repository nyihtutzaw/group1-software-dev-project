import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { MobileMenu } from './MobileMenu'
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

describe('MobileMenu', () => {
  it('opens the full menu, System pages included, from the hamburger button', async () => {
    renderWithProviders(<MobileMenu items={navFor('admin')} user={makeUser('admin')} />, {
      route: '/system/tutorials',
    })
    const button = screen.getByRole('button', { name: 'Open menu' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await userEvent.click(button)

    const drawer = screen.getByRole('dialog', { name: 'Menu' })
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(within(drawer).getByRole('link', { name: 'Ledger' })).toHaveAttribute('href', '/ledger')
    expect(within(drawer).getByRole('button', { name: 'System' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(within(drawer).getByRole('link', { name: 'Tutorials' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(within(drawer).getByText('Registry admin')).toBeInTheDocument()
  })

  it('closes when a menu link is chosen', async () => {
    renderWithProviders(<MobileMenu items={navFor('admin')} user={makeUser('admin')} />)
    await userEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('link', { name: 'Registry' }),
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes with Escape or the close button and returns focus to the hamburger', async () => {
    renderWithProviders(<MobileMenu items={navFor('admin')} user={makeUser('admin')} />)
    const button = screen.getByRole('button', { name: 'Open menu' })

    await userEvent.click(button)
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(button).toHaveFocus()

    await userEvent.click(button)
    await userEvent.click(screen.getByRole('button', { name: 'Close menu' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows only public pages when signed out', async () => {
    renderWithProviders(<MobileMenu items={navFor(null)} user={null} />)
    await userEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const drawer = screen.getByRole('dialog')
    expect(within(drawer).getByRole('link', { name: 'Registry' })).toBeInTheDocument()
    expect(within(drawer).queryByRole('link', { name: 'Ledger' })).not.toBeInTheDocument()
  })
})
