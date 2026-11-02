import { type KeyboardEvent, type ReactNode, useRef } from 'react'

import { cn } from '@/lib/cn'

export type TabItem<T extends string> = { id: T; label: ReactNode; count?: number }

/**
 * Underlined tabs. Pair each tab with a <TabPanel> using the same `idBase` and id.
 *
 *   <Tabs idBase="queue" label="Queue" tabs={[{ id: 'open', label: 'Open', count: 3 }]}
 *     value={tab} onChange={setTab} />
 *   <TabPanel idBase="queue" id={tab}>…</TabPanel>
 */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
  idBase,
  className,
}: {
  tabs: TabItem<T>[]
  value: T
  onChange: (id: T) => void
  label: string
  idBase: string
  className?: string
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function onKeyDown(event: KeyboardEvent, index: number) {
    const last = tabs.length - 1
    const next =
      event.key === 'ArrowRight'
        ? index === last
          ? 0
          : index + 1
        : event.key === 'ArrowLeft'
          ? index === 0
            ? last
            : index - 1
          : event.key === 'Home'
            ? 0
            : event.key === 'End'
              ? last
              : null
    if (next === null) return
    event.preventDefault()
    refs.current[next]?.focus()
    onChange(tabs[next].id)
  }

  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn('mb-5 flex gap-1 overflow-x-auto border-b border-line', className)}
    >
      {tabs.map((tab, index) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[index] = el
            }}
            type="button"
            role="tab"
            id={`${idBase}-tab-${tab.id}`}
            aria-controls={`${idBase}-panel-${tab.id}`}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={cn(
              '-mb-px flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors',
              active
                ? 'border-accent text-accent'
                : 'border-transparent text-faint hover:border-line-strong hover:text-ink',
            )}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span
                className={cn(
                  'min-w-5 rounded-full px-1.5 text-center text-xs leading-5 font-semibold tabular-nums',
                  active ? 'bg-accent-soft text-accent' : 'bg-surface-3 text-muted',
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export function TabPanel({
  idBase,
  id,
  children,
}: {
  idBase: string
  id: string
  children: ReactNode
}) {
  return (
    <div role="tabpanel" id={`${idBase}-panel-${id}`} aria-labelledby={`${idBase}-tab-${id}`}>
      {children}
    </div>
  )
}
