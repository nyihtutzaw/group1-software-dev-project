import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'

import type { User } from '@/auth/types'

/**
 * Render with router + react-query, optionally signed in as `user`.
 *   renderWithProviders(<App />, { route: '/verify', user: makeUser('verifier') })
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', user = null }: { route?: string; user?: User | null } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(['auth', 'me'], user)
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

export function makeUser(role: User['role']): User {
  return { id: 1, email: `${role}@test.local`, full_name: 'Test User', organization: null, role }
}

/** Make every fetch() resolve with `body` (default: an empty list). */
export function mockFetch(body: unknown = []) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(body))
}
