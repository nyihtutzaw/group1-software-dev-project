import { useCallback, useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark'

/** localStorage key; index.html reads it too so the saved theme applies before first paint. */
export const THEME_KEY = 'crvr-theme'

/** Light unless the user picked dark; the system setting is deliberately ignored. */
function current(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

const listeners = new Set<() => void>()

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** The active theme (the user's choice, else light) and a toggle that remembers it. */
export function useTheme() {
  const theme = useSyncExternalStore(subscribe, current, () => 'light' as Theme)
  const setTheme = useCallback((next: Theme) => {
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {
      // private mode: the choice lasts for this page only
    }
    listeners.forEach((listener) => listener())
  }, [])
  const toggle = useCallback(() => setTheme(current() === 'dark' ? 'light' : 'dark'), [setTheme])
  return { theme, setTheme, toggle }
}
