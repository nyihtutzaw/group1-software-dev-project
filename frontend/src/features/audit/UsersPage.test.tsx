import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { UsersPage } from './UsersPage'

const USERS = [
  {
    id: 1,
    email: 'admin@example.com',
    full_name: 'Registry Admin',
    organization: 'Registry',
    role: 'admin',
    is_active: true,
  },
  {
    id: 2,
    email: 'dev@example.com',
    full_name: 'Project Developer',
    organization: null,
    role: 'developer',
    is_active: true,
  },
]

describe('UsersPage', () => {
  it('does not request the user list for non-admins', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    renderWithProviders(<UsersPage />, { user: makeUser('buyer') })

    expect(screen.getByText('Admin access required')).toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('lists accounts and prevents an admin from changing their own access', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(USERS))

    renderWithProviders(<UsersPage />, { user: makeUser('admin') })

    expect(await screen.findByText('Project Developer')).toBeInTheDocument()
    expect(screen.getByText('dev@example.com')).toBeInTheDocument()

    const self = screen.getByText('admin@example.com').closest('li')
    if (!self) throw new Error('Current admin row was not rendered')
    expect(within(self).getByRole('button', { name: 'Deactivate' })).toBeDisabled()
    expect(
      within(self).getByRole('combobox', { name: 'Role for admin@example.com' }),
    ).toBeDisabled()
  })

  it('creates a user and clears the initial password from the form', async () => {
    let createBody: Record<string, unknown> | null = null
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') {
        createBody = JSON.parse(String(init.body)) as Record<string, unknown>
        return Response.json({ ...USERS[1], id: 3, email: 'new@example.com' }, { status: 201 })
      }
      return Response.json(USERS)
    })

    const user = userEvent.setup()
    renderWithProviders(<UsersPage />, { user: makeUser('admin') })

    await user.type(await screen.findByLabelText('Full name'), 'New User')
    await user.type(screen.getByLabelText('Email'), 'new@example.com')
    await user.selectOptions(screen.getByLabelText('Role', { selector: 'select' }), 'verifier')
    await user.type(screen.getByLabelText('Initial password'), 'a-long-initial-password')
    await user.click(screen.getByRole('button', { name: 'Create user' }))

    expect(await screen.findByText('Account created')).toBeInTheDocument()
    await waitFor(() => expect(createBody).not.toBeNull())
    expect(createBody).toMatchObject({
      email: 'new@example.com',
      full_name: 'New User',
      role: 'verifier',
      initial_password: 'a-long-initial-password',
    })
    expect(screen.getByLabelText('Initial password')).toHaveValue('')
    expect(fetchSpy).toHaveBeenCalled()
  })

  it('updates a user role', async () => {
    const updatedUser = { ...USERS[1], role: 'buyer' }
    let updated = false
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'PATCH') {
        updated = true
        return Response.json(updatedUser)
      }
      return Response.json(updated ? [USERS[0], updatedUser] : USERS)
    })

    const user = userEvent.setup()
    renderWithProviders(<UsersPage />, { user: makeUser('admin') })

    const role = await screen.findByRole('combobox', { name: 'Role for dev@example.com' })
    await user.selectOptions(role, 'buyer')

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/admin/users/2',
        expect.objectContaining({ method: 'PATCH' }),
      ),
    )
    await waitFor(() => expect(role).toHaveValue('buyer'))
  })

  it('confirms account deactivation before sending the request', async () => {
    let deactivated = false
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'PATCH') {
        deactivated = true
        return Response.json({ ...USERS[1], is_active: false })
      }
      return Response.json(deactivated ? [USERS[0], { ...USERS[1], is_active: false }] : USERS)
    })

    const user = userEvent.setup()
    renderWithProviders(<UsersPage />, { user: makeUser('admin') })

    const buttons = await screen.findAllByRole('button', { name: /^Deactivate$/ })
    await user.click(buttons[1])
    expect(screen.getByRole('dialog')).toHaveTextContent(
      'Project Developer will no longer be able to sign in.',
    )
    await user.click(screen.getByRole('button', { name: 'Deactivate account' }))

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/admin/users/2',
        expect.objectContaining({ method: 'PATCH' }),
      ),
    )
  })
})
