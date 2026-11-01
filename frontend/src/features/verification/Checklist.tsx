import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import type { CheckLine } from './api'

export function Checklist({
  items,
  checked,
  editable,
  onToggle,
}: {
  items: CheckLine[]
  checked: Record<string, boolean>
  editable: boolean
  onToggle: (key: string) => void
}) {
  return (
    <div>
      {items.map((item) => {
        const on = checked[item.key] ?? false
        return (
          <button
            key={item.key}
            type="button"
            role="checkbox"
            aria-checked={on}
            disabled={!editable}
            onClick={() => onToggle(item.key)}
            className="flex w-full items-start gap-[11px] border-b border-line px-3.5 py-3 text-left last:border-b-0 disabled:cursor-default"
          >
            <span
              className={cn(
                'mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border',
                on
                  ? 'border-accent bg-accent text-on-accent'
                  : 'border-line-strong bg-surface text-transparent',
              )}
            >
              <Icon name="check" className="size-3.5" strokeWidth={3} />
            </span>
            <span className="min-w-0">
              <b className="block text-sm font-medium">{item.label}</b>
              <span className="mt-0.5 block text-xs text-faint">{item.source}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
