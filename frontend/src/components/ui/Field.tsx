import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

import { cn } from '@/lib/cn'

/*
 * Form fields: a Card holds stacked Fields, each a label above a bordered control.
 *
 *   <Card>
 *     <Field label="Project name" htmlFor="name"><Input id="name" /></Field>
 *     <FieldRow>…two Fields side by side…</FieldRow>
 *   </Card>
 */

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string
  htmlFor: string
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="px-4 py-2.5 first:pt-4 last:pb-4">
      <label htmlFor={htmlFor} className="mb-1.5 block text-[13px] font-medium text-muted">
        {label}
      </label>
      {children}
      {hint && !error && <p className="mt-1.5 text-xs text-faint">{hint}</p>}
      {error && <p className="mt-1.5 text-xs font-medium text-warn">{error}</p>}
    </div>
  )
}

export function FieldRow({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 first:pt-1.5 last:pb-1.5 [&>div]:py-2.5! [&>div:first-child]:pr-2 [&>div:last-child]:pl-2">
      {children}
    </div>
  )
}

const control =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink shadow-card transition-[border-color,box-shadow] placeholder:text-faint focus:border-accent focus:ring-3 focus:ring-accent/15 focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-faint aria-invalid:border-warn'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(control, className)} {...props} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, 'pr-8', className)} {...props} />
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(control, 'resize-y', className)} {...props} />
}
