import { cn } from '@/lib/cn'

function initials(name: string): string {
  return name
    .replace(/^Dr\.?\s+/i, '')
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      className={cn(
        'grid size-9 flex-none place-items-center rounded-full bg-accent-soft text-[13px] font-semibold text-accent',
        className,
      )}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  )
}
