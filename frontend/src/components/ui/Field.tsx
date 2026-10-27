import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

import { cn } from '@/lib/cn'

/*
 * Form fields as in the mock-up: a Card holds stacked Fields separated by lines,
 * each with a small mono uppercase label above a borderless control.
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
    <div className="border-b border-line px-3.5 py-3 last:border-b-0">
      <label
        htmlFor={htmlFor}
        className="mb-[5px] block font-mono text-[11px] font-semibold tracking-[0.1em] text-faint uppercase"
      >
        {label}
      </label>
      {children}
      {hint && !error && <p className="mt-[5px] text-xs text-faint">{hint}</p>}
      {error && <p className="mt-[5px] text-xs text-warn">{error}</p>}
    </div>
  )
}

export function FieldRow({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 border-b border-line last:border-b-0 [&>div]:border-b-0 [&>div:not(:last-child)]:border-r [&>div]:border-line">
      {children}
    </div>
  )
}

const control =
  'w-full border-0 bg-transparent p-0 text-[15px] text-ink placeholder:text-faint focus:outline-none'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(control, className)} {...props} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, className)} {...props} />
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(control, 'resize-y', className)} {...props} />
}
