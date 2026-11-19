import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { THEME_KEY, useTheme } from './theme'

afterEach(() => {
  delete document.documentElement.dataset.theme
  localStorage.clear()
  vi.unstubAllGlobals()
})

describe('useTheme', () => {
  it('is light by default, even when the system prefers dark', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('dark'),
      addEventListener: () => {},
      removeEventListener: () => {},
    }))
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
  })

  it('switches to dark when the user picks it, and remembers the choice', () => {
    const { result } = renderHook(() => useTheme())
    act(() => result.current.toggle())
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')
  })
})
