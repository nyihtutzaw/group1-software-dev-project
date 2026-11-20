import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ErrorBoundary } from './ErrorBoundary'

let explode = true
function Page() {
  if (explode) throw new Error('l is not a function')
  return <p>Page content</p>
}

beforeEach(() => {
  explode = true
  vi.spyOn(console, 'error').mockImplementation(() => {}) // React and the boundary both log
})
afterEach(() => vi.restoreAllMocks())

describe('ErrorBoundary', () => {
  it('shows an error card instead of a blank screen, with the technical message', () => {
    render(
      <ErrorBoundary resetKey="/system/roles-access">
        <Page />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong on this page')
    expect(screen.getByText('l is not a function')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reload the page' })).toBeInTheDocument()
  })

  it('renders the page again after Try again', async () => {
    render(
      <ErrorBoundary resetKey="/a">
        <Page />
      </ErrorBoundary>,
    )
    explode = false

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(screen.getByText('Page content')).toBeInTheDocument()
  })

  it('clears the error when another page is opened', () => {
    const { rerender } = render(
      <ErrorBoundary resetKey="/a">
        <Page />
      </ErrorBoundary>,
    )
    explode = false

    rerender(
      <ErrorBoundary resetKey="/system/demo-data">
        <Page />
      </ErrorBoundary>,
    )

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Page content')).toBeInTheDocument()
  })
})
