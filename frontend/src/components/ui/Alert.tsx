import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

import { Icon, type IconName } from './Icon'

type Tone = 'warn' | 'ok'

const TONES: Record<Tone, { box: string; icon: string; name: IconName }> = {
  warn: { box: 'bg-warn-soft border-warn/25', icon: 'text-warn', name: 'alert' },
  ok: { box: 'bg-ok-soft border-ok/25', icon: 'text-ok', name: 'check' },
}

export function Alert({
  tone = 'warn',
  title,
  icon,
  children,
  className,
}: {
  tone?: Tone
  title: ReactNode
  icon?: IconName
  children?: ReactNode
  className?: string
}) {
  const t = TONES[tone]
  return (
    <div
      role={tone === 'warn' ? 'alert' : 'status'}
      className={cn(
        'grid grid-cols-[auto_1fr] gap-3 rounded-xl border px-4 py-3 text-[13px] text-muted',
        t.box,
        className,
      )}
    >
      <Icon name={icon ?? t.name} strokeWidth={2} className={cn('mt-px size-[18px]', t.icon)} />
      <div>
        <b className="mb-0.5 block text-sm font-semibold text-ink">{title}</b>
        {children}
      </div>
    </div>
  )
}
