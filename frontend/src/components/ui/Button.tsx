import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Variant = 'primary' | 'ghost' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-on-accent hover:bg-accent-ink',
  ghost: 'border border-line-strong text-muted hover:bg-surface-2',
  danger: 'bg-warn text-white hover:opacity-90',
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }

export function Button({ variant = 'primary', className, type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'block w-full rounded-[11px] p-[13px] text-center text-[15px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  )
}

/** Two buttons side by side, stacked on narrow phones (mock-up `.btnrow`). */
export function ButtonRow({ children }: { children: ReactNode }) {
  return <div className="mt-3.5 grid grid-cols-1 gap-[9px] min-[421px]:grid-cols-2">{children}</div>
}
