import type { ReactNode } from 'react'

import { Card } from './Card'
import { Icon, type IconName } from './Icon'

/** Placeholder block for a page or list with nothing to show yet. */
export function EmptyState({
  icon,
  title,
  children,
}: {
  icon: IconName
  title: ReactNode
  children?: ReactNode
}) {
  return (
    <Card className="grid justify-items-center gap-2 px-4 py-10 text-center">
      <span className="mb-1 grid size-11 place-items-center rounded-full bg-accent-soft text-accent ring-8 ring-accent-soft/40">
        <Icon name={icon} className="size-[22px]" />
      </span>
      <b className="text-[15px] font-semibold text-ink">{title}</b>
      {children && <div className="max-w-md text-[13px] text-faint">{children}</div>}
    </Card>
  )
}
