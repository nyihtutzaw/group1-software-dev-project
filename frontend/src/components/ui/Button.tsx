import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Variant = 'primary' | 'ghost' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'border-accent bg-accent text-on-accent hover:border-accent-ink hover:bg-accent-ink',
  ghost: 'border-line-strong bg-surface text-ink hover:bg-surface-2',
  danger: 'border-warn bg-warn text-white hover:opacity-90',
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }

export function Button({ variant = 'primary', className, type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'block w-full rounded-lg border px-4 py-2.5 text-center text-sm font-semibold shadow-card transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  )
}

/** Two buttons side by side, stacked on narrow phones (mock-up `.btnrow`). */
export function ButtonRow({ children }: { children: ReactNode }) {
  return <div className="mt-4 grid grid-cols-1 gap-2.5 min-[421px]:grid-cols-2">{children}</div>
}
