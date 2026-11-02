import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export type ChipTone = 'ok' | 'wait' | 'warn' | 'draft' | 'accent'

const TONES: Record<ChipTone, string> = {
  ok: 'bg-ok-soft text-ok',
  wait: 'bg-wait-soft text-wait',
  warn: 'bg-warn-soft text-warn',
  draft: 'bg-surface-3 text-muted',
  accent: 'bg-accent-soft text-accent',
}

/** Small status badge with a dot, e.g. VERIFIED, OVERDUE, SEALED. */
export function StatusChip({ tone = 'draft', children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-current/15 px-2 py-0.5 text-[11px] leading-[18px] font-semibold tracking-[0.03em] whitespace-nowrap',
        'before:size-1.5 before:flex-none before:rounded-full before:bg-current',
        TONES[tone],
      )}
    >
      {children}
    </span>
  )
}
