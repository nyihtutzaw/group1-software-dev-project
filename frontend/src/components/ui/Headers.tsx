import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Icon } from './Icon'

/**
 * Page title with an optional subtitle, a back link above it (detail pages) and actions on the
 * right (a status chip, buttons).
 */
export function PageHeader({
  title,
  subtitle,
  back,
  actions,
}: {
  title: ReactNode
  subtitle?: ReactNode
  back?: { to: string; label: string }
  actions?: ReactNode
}) {
  return (
    <header className="mb-6">
      {back && (
        <Link
          to={back.to}
          className="mb-3 inline-flex items-center gap-1 text-[13px] font-medium text-faint hover:text-accent"
        >
          <Icon name="chevron" strokeWidth={2} className="size-4 rotate-180" />
          {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h1 className="text-[22px] leading-tight font-semibold tracking-[-0.02em] text-balance desk:text-[26px]">
            {title}
          </h1>
          {subtitle && <p className="mt-1 text-sm text-faint">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-none items-center gap-2 pt-1">{actions}</div>}
      </div>
    </header>
  )
}

/** Section heading with an optional action on the right. */
export function SectionHeader({ title, action }: { title: ReactNode; action?: ReactNode }) {
  return (
    <div
      data-section-header
      className="mt-8 mb-3 flex items-center justify-between gap-3 first:mt-1"
    >
      <h3 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h3>
      {action && <div className="text-[13px] font-semibold text-accent">{action}</div>}
    </div>
  )
}
