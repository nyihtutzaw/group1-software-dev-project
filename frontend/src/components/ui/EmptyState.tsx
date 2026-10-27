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
      <span className="grid size-11 place-items-center rounded-xl bg-accent-soft text-accent">
        <Icon name={icon} className="size-[22px]" />
      </span>
      <b className="text-[15px] font-semibold">{title}</b>
      {children && <div className="max-w-md text-[13.5px] text-faint">{children}</div>}
    </Card>
  )
}
