import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export type KeyValueItem = { label: string; value: ReactNode; mono?: boolean }

/** Label/value list as in the traceability and overlap panels. Wrap in a Card. */
export function KeyValue({ items }: { items: KeyValueItem[] }) {
  return (
    <dl className="grid grid-cols-[auto_1fr]">
      {items.map(({ label, value, mono }) => (
        <div key={label} className="contents [&:last-child>*]:border-b-0">
          <dt className="border-b border-line px-3.5 py-2.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap text-faint">
            {label}
          </dt>
          <dd
            className={cn(
              'min-w-0 border-b border-line py-2.5 pr-3.5 pl-4 text-right text-sm font-medium wrap-anywhere',
              mono && 'font-mono',
            )}
          >
            {value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
