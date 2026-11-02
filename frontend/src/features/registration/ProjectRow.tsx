import { Link } from 'react-router'

import { Icon, StatusChip } from '@/components/ui'
import { cn } from '@/lib/cn'

import { isDraft, projectChip, projectMeta, projectProgress } from './format'
import type { ProjectOut } from './types'

/** Four-segment progress bar (mock-up `.steps`); the last done segment can show a warning. */
export function ProgressSteps({
  done,
  warn = false,
  total = 4,
  className,
}: {
  done: number
  warn?: boolean
  total?: number
  className?: string
}) {
  return (
    <span className={cn('flex gap-1', className)} aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <i
          key={i}
          className={cn(
            'h-1 flex-1 rounded-sm',
            i >= done ? 'bg-surface-3' : warn && i === done - 1 ? 'bg-warn' : 'bg-accent',
          )}
        />
      ))}
    </span>
  )
}

/** The little parcel drawing on each project row (mock-up `.thumb`). */
function MiniMap({ warn }: { warn: boolean }) {
  return (
    <span className="grid size-11 flex-none place-items-center overflow-hidden rounded-[9px] bg-surface-3">
      <svg viewBox="0 0 44 44" className="block size-11" aria-hidden="true">
        <rect width="44" height="44" className="fill-surface-3" />
        <path d="M0 30 Q12 25 22 29 T44 27 L44 44 L0 44Z" className="fill-line" />
        <polygon
          points="10,10 26,8 33,19 27,31 13,30 8,19"
          className={warn ? 'text-warn' : 'text-accent'}
          fill="currentColor"
          fillOpacity={0.3}
          stroke="currentColor"
          strokeWidth={2}
        />
      </svg>
    </span>
  )
}

/** One project on the dashboard (mock-up `.prow`). Drafts open the form, others the detail page. */
export function ProjectRow({ project, editable }: { project: ProjectOut; editable: boolean }) {
  const chip = projectChip(project)
  const progress = projectProgress(project)
  const to =
    editable && isDraft(project) ? `/projects/${project.id}/edit` : `/projects/${project.id}`

  return (
    <Link
      to={to}
      className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 rounded-xl border border-line bg-surface px-3.5 py-[13px] text-left shadow-card hover:border-line-strong"
    >
      <MiniMap warn={project.overlap} />
      <span className="min-w-0">
        <b className="block text-[14.5px] leading-tight font-semibold">{project.name}</b>
        <span className="mt-[3px] block font-mono text-xs text-faint">{project.code}</span>
        <span className="mt-[3px] block truncate text-xs text-faint">{projectMeta(project)}</span>
        <ProgressSteps done={progress.done} warn={progress.warn} className="mt-[9px]" />
      </span>
      <span className="grid justify-items-end gap-2">
        <StatusChip tone={chip.tone}>{chip.label}</StatusChip>
        <Icon name="chevron" strokeWidth={2} className="size-4 text-faint" />
      </span>
    </Link>
  )
}
