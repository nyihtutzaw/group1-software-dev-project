import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export type ChipTone = 'ok' | 'wait' | 'warn' | 'draft' | 'accent'

const TONES: Record<ChipTone, string> = {
  ok: 'bg-ok-soft text-ok',
  wait: 'bg-wait-soft text-wait',
  warn: 'bg-warn-soft text-warn',
  draft: 'bg-surface-3 text-faint',
  accent: 'bg-accent-soft text-accent',
}

/** Small uppercase status pill with a dot, e.g. VERIFIED, OVERDUE, SEALED. */
export function StatusChip({ tone = 'draft', children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-[5px] whitespace-nowrap rounded-full px-2 py-[3px] font-mono text-[11px] font-semibold tracking-[0.02em]',
        'before:size-1.5 before:flex-none before:rounded-full before:bg-current',
        TONES[tone],
      )}
    >
      {children}
    </span>
  )
}
