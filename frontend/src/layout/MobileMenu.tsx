import { type MouseEvent, useCallback, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import type { User } from '@/auth/types'
import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import { Brand } from './Brand'
import type { NavItem } from './nav'
import { MenuPanel } from './Sidebar'
import { iconButton } from './ThemeToggle'

/**
 * Phone menu: a hamburger button in the top bar that slides in the sidebar menu as a drawer.
 * Closes on a menu link, the close button, a tap outside or Escape. Hidden on desktop.
 */
export function MobileMenu({ items, user }: { items: NavItem[]; user: User | null }) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const close = useCallback(() => setOpen(false), [])

  useEffect(() => {
    if (!open) return
    const opener = button.current
    panel.current?.focus()
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      opener?.focus()
    }
  }, [open, close])

  // Any menu link closes the drawer, including the page you are already on
  const onPanelClick = (event: MouseEvent) => {
    if ((event.target as HTMLElement).closest('a')) close()
  }

  return (
    <>
      <button
        ref={button}
        type="button"
        className={cn(iconButton, '-ml-1 desk:hidden')}
        aria-label="Open menu"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen(true)}
      >
        <Icon name="menu" strokeWidth={2} className="size-[19px]" />
      </button>
      {open &&
        createPortal(
          <div className="fixed inset-0 z-50 desk:hidden">
            <div
              className="drawer-fade absolute inset-0 bg-overlay"
              onClick={close}
              aria-hidden="true"
            />
            <div
              ref={panel}
              id={panelId}
              role="dialog"
              aria-modal="true"
              aria-label="Menu"
              tabIndex={-1}
              onClick={onPanelClick}
              className="drawer-in absolute inset-y-0 left-0 flex w-[min(300px,86vw)] flex-col border-r border-line bg-surface pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-lg focus:outline-none"
            >
              <div className="flex h-14 flex-none items-center justify-between border-b border-line pr-2 pl-4">
                <Brand />
                <button
                  type="button"
                  className={iconButton}
                  aria-label="Close menu"
                  onClick={close}
                >
                  <Icon name="close" strokeWidth={2} className="size-[17px]" />
                </button>
              </div>
              <MenuPanel items={items} user={user} />
            </div>
          </div>,
          document.body,
        )}
    </>
  )
}
