import { cn } from '@/lib/cn'

import type { Mark, TutorialStep } from './types'

/** Numbered badge shared by the marks on the image and the legend beside it. */
export function MarkNumber({ n, className }: { n: number; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'grid size-6 flex-none place-items-center rounded-full bg-purple text-xs font-bold text-bg shadow-card',
        className,
      )}
    >
      {n}
    </span>
  )
}

// Marks are drawn a few pixels larger than the element they point at.
const PAD = 5

const BADGE_CORNER: Record<NonNullable<Mark['badge']>, string> = {
  tl: '-top-2.5 -left-2.5',
  tr: '-top-2.5 -right-2.5',
  bl: '-bottom-2.5 -left-2.5',
  br: '-right-2.5 -bottom-2.5',
}

function markStyle(m: Mark) {
  return {
    left: `calc(${m.x}% - ${PAD}px)`,
    top: `calc(${m.y}% - ${PAD}px)`,
    width: `calc(${m.w}% + ${PAD * 2}px)`,
    height: `calc(${m.h}% + ${PAD * 2}px)`,
  }
}

/**
 * A screenshot with numbered boxes over it. `active` highlights one mark and dims the rest;
 * hovering a mark reports it through `onActive` so the legend can follow.
 */
export function AnnotatedScreenshot({
  step,
  active,
  onActive,
}: {
  step: TutorialStep
  active: number | null
  onActive: (index: number | null) => void
}) {
  const [width, height] = step.size
  return (
    <figure className="relative">
      <a href={step.image} target="_blank" rel="noreferrer" title="Open the full-size screenshot">
        <img
          src={step.image}
          alt={step.alt}
          width={width}
          height={height}
          className="block h-auto w-full rounded-lg border border-line bg-surface-2"
        />
      </a>
      {step.marks.map((mark, i) => (
        <div
          key={mark.label}
          data-testid="tutorial-mark"
          aria-hidden="true"
          onMouseEnter={() => onActive(i)}
          onMouseLeave={() => onActive(null)}
          style={markStyle(mark)}
          className={cn(
            'absolute rounded-md border-2 border-purple transition-[opacity,background-color,box-shadow]',
            active === null || active === i ? 'opacity-100' : 'opacity-25',
            active === i && 'bg-purple/10 shadow-[0_0_0_4px] shadow-purple/25',
          )}
        >
          <MarkNumber
            n={i + 1}
            className={cn('absolute size-5 text-[11px]', BADGE_CORNER[mark.badge ?? 'tr'])}
          />
        </div>
      ))}
    </figure>
  )
}
