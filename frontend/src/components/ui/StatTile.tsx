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
    <div className="flex flex-col-reverse justify-end gap-2 rounded-xl border border-line bg-surface px-4 py-3.5 shadow-card">
      <b
        className={cn(
          'block text-[26px] leading-none font-semibold tracking-[-0.02em] tabular-nums',
          TONES[tone],
        )}
      >
        {value}
      </b>
      <span className="block text-[13px] leading-snug font-medium text-faint">{label}</span>
    </div>
  )
}

/** Responsive grid of StatTiles (two per row on phones). */
export function StatTiles({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(160px,45%),1fr))] gap-3">
      {children}
    </div>
  )
}
