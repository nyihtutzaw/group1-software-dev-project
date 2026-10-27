import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from './App'
import { makeUser, mockFetch, renderWithProviders } from './test/render'

describe('App routing', () => {
  it('sends signed-out visitors to the sign-in page', () => {
    mockFetch()
    renderWithProviders(<App />, { route: '/verify' })

    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('lets anyone open the public registry', () => {
    renderWithProviders(<App />, { route: '/registry' })

    expect(screen.getByRole('heading', { name: 'Public registry' })).toBeInTheDocument()
  })

  it('shows the page and role-based menu to an allowed role', () => {
    renderWithProviders(<App />, { route: '/verify', user: makeUser('verifier') })

    expect(screen.getByRole('heading', { name: 'Verification queue' })).toBeInTheDocument()
    const menu = screen.getByRole('navigation', { name: 'Main' })
    expect(menu).toHaveTextContent('Verify')
    expect(menu).not.toHaveTextContent('Submit')
  })

  it('blocks a role that may not open the page', () => {
    renderWithProviders(<App />, { route: '/verify', user: makeUser('buyer') })

    expect(screen.getByText('Your role cannot open this page')).toBeInTheDocument()
  })
})
