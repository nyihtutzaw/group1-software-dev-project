import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DemoAccount } from '@/auth/types'
import { mockFetch, renderWithProviders } from '@/test/render'

import { LoginPage } from './LoginPage'

const account = (password: string | null): DemoAccount => ({
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

  it('only fills in the email when the demo password is private (hosted demo)', async () => {
    const fetch = mockFetch([account(null)])
    renderWithProviders(<LoginPage />)

    expect(await screen.findByText('password from your instructor')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Malee Wong/ }))

    expect(screen.getByLabelText('Email')).toHaveValue('verifier@crvr.local')
    expect(screen.getByLabelText('Password')).toHaveFocus()
    expect(fetch.mock.calls.some(([url]) => url === '/api/auth/login')).toBe(false)
  })
})
