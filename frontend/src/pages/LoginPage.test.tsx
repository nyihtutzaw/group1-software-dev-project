import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DemoAccount } from '@/auth/types'
import { mockFetch, renderWithProviders } from '@/test/render'

import { LoginPage } from './LoginPage'

const account = (password: string): DemoAccount => ({
  email: 'verifier@crvr.local',
  full_name: 'Malee Wong',
  role: 'verifier',
  password,
})

describe('LoginPage demo accounts', () => {
  it('signs in with one click when the demo password is public (development)', async () => {
    const fetch = mockFetch([account('crvr-demo')])
    renderWithProviders(<LoginPage />)

    expect(await screen.findByText('password crvr-demo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Malee Wong/ }))

    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/auth/login', expect.anything()))
    const login = fetch.mock.calls.find(([url]) => url === '/api/auth/login')
    expect(JSON.parse(String(login?.[1]?.body))).toEqual({
      email: 'verifier@crvr.local',
      password: 'crvr-demo',
    })
  })

  it('shows no demo accounts when the server lists none (hosted demo)', async () => {
    const fetch = mockFetch([])
    renderWithProviders(<LoginPage />)

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith('/api/auth/demo-accounts', expect.anything()),
    )
    expect(screen.queryByText('Demo accounts')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })
})
