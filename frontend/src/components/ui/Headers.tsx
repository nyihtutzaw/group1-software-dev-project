import type { ReactNode } from 'react'

/** Page title with an optional grey subtitle line. */
export function PageHeader({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-[22px] leading-tight font-semibold tracking-[-0.02em] text-balance desk:text-[26px]">
        {title}
      </h1>
      {subtitle && <p className="mt-1 text-sm text-faint">{subtitle}</p>}
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
