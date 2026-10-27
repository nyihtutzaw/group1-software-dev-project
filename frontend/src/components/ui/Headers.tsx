import type { ReactNode } from 'react'

/** Page title (serif) with an optional grey subtitle line. */
export function PageHeader({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <header className="mb-[18px]">
      <h1 className="mb-1 font-serif text-2xl font-bold tracking-[-0.015em] text-balance desk:text-[29px]">
        {title}
      </h1>
      {subtitle && <p className="text-[13.5px] text-faint">{subtitle}</p>}
    </header>
  )
}

/** Small mono uppercase section heading with an optional action on the right. */
export function SectionHeader({ title, action }: { title: ReactNode; action?: ReactNode }) {
  return (
    <div className="mt-[26px] mb-[11px] flex items-baseline justify-between gap-3 first:mt-1.5">
      <h3 className="font-mono text-xs font-semibold tracking-[0.12em] text-faint uppercase">
        {title}
      </h3>
      {action && <div className="text-[12.5px] font-semibold text-accent">{action}</div>}
    </div>
  )
}
