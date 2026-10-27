import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Tone = 'default' | 'accent' | 'ok' | 'warn'

const TONES: Record<Tone, string> = {
  default: 'text-ink',
  accent: 'text-accent',
  ok: 'text-ok',
  warn: 'text-warn',
}

export function StatTile({
  value,
  label,
  tone = 'default',
}: {
  value: ReactNode
  label: ReactNode
  tone?: Tone
}) {
  return (
    <div className="rounded-xl border border-line bg-surface px-3.5 py-[13px]">
      <b
        className={cn(
          'block font-serif text-[27px] leading-none font-bold tabular-nums',
          TONES[tone],
        )}
      >
        {value}
      </b>
      <span className="mt-1.5 block text-[11.5px] leading-snug text-faint">{label}</span>
    </div>
  )
}

/** Responsive grid of StatTiles (two per row on phones). */
export function StatTiles({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(140px,45%),1fr))] gap-2.5">
      {children}
    </div>
  )
}
