import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { THEME_KEY } from '@/lib/theme'

import { ThemeToggle } from './ThemeToggle'

afterEach(() => {
  delete document.documentElement.dataset.theme
  localStorage.clear()
})

describe('ThemeToggle', () => {
  it('switches between light and dark and remembers the choice', () => {
    render(<ThemeToggle />)

    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')

    fireEvent.click(screen.getByRole('button', { name: 'Switch to light theme' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem(THEME_KEY)).toBe('light')
  })
})
