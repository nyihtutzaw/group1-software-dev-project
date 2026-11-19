import { type ReactNode, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import { ROLE_LABELS, type Role } from '@/auth/types'
import {
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Icon,
  KeyValue,
  PageHeader,
  StatusChip,
} from '@/components/ui'
import { isUnder, NAV_ITEMS } from '@/layout/nav'
import { cn } from '@/lib/cn'

import { AnnotatedScreenshot, MarkNumber } from './AnnotatedScreenshot'
import { TUTORIALS, tutorialById } from './content'
import type { Tutorial, TutorialStep } from './types'

/** True when `role` may open the page at `path` (so a "Open this page" link would work). */
function canOpen(path: string, role: Role | undefined) {
  const item = NAV_ITEMS.filter((i) => isUnder(i, path)).sort(
    (a, b) => b.path.length - a.path.length,
  )[0]
  return Boolean(item && role && item.roles.includes(role))
}

function StepList({
  steps,
  index,
  onPick,
}: {
  steps: TutorialStep[]
  index: number
  onPick: (i: number) => void
}) {
  return (
    <ol aria-label="Steps" className="-mx-1 mb-5 flex gap-2 overflow-x-auto px-1 pb-1">
      {steps.map((s, i) => (
        <li key={s.title} className="flex-none">
          <button
            type="button"
            aria-current={i === index ? 'step' : undefined}
            onClick={() => onPick(i)}
            className={cn(
              'flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12.5px] font-medium whitespace-nowrap transition-colors',
              i === index
                ? 'border-accent bg-accent text-on-accent'
                : i < index
                  ? 'border-accent/30 bg-accent-soft text-accent hover:border-accent'
                  : 'border-line bg-surface text-muted hover:border-line-strong hover:text-ink',
            )}
          >
            <span className="font-mono text-[11px] opacity-80">{i + 1}</span>
            {s.title}
          </button>
        </li>
      ))}
    </ol>
  )
}

function Legend({
  step,
  active,
  onActive,
}: {
  step: TutorialStep
  active: number | null
  onActive: (i: number | null) => void
}) {
  return (
    <ol aria-label="On this screen" className="grid gap-0.5">
      {step.marks.map((mark, i) => (
        <li key={mark.label}>
          <button
            type="button"
            onMouseEnter={() => onActive(i)}
            onMouseLeave={() => onActive(null)}
            onFocus={() => onActive(i)}
            onBlur={() => onActive(null)}
            className={cn(
              'flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] text-muted transition-colors',
              active === i ? 'bg-surface-2 text-ink' : 'hover:bg-surface-2',
            )}
          >
            <MarkNumber n={i + 1} className="mt-px" />
            <span>{mark.label}</span>
          </button>
        </li>
      ))}
    </ol>
  )
}

function SidePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="overflow-hidden">
      <h3 className="border-b border-line px-4 py-3 text-sm font-semibold text-ink">{title}</h3>
      {children}
    </Card>
  )
}

function SampleFiles({ tutorial }: { tutorial: Tutorial }) {
  return (
    <SidePanel title="Sample files">
      <ul className="divide-y divide-line">
        {tutorial.files.map((f) => (
          <li key={f.file} className="flex items-start gap-3 px-4 py-3">
            <Icon name="file" className="mt-0.5 size-[18px] flex-none text-faint" />
            <div className="min-w-0 flex-1">
              <a
                href={f.file}
                download
                className="text-[13px] font-semibold text-accent hover:underline"
              >
                {f.label}
              </a>
              <p className="text-xs text-faint">{f.description}</p>
            </div>
          </li>
        ))}
      </ul>
    </SidePanel>
  )
}

/** System › Tutorials › one feature: its steps, one annotated screenshot at a time. */
export function TutorialPage() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const [active, setActive] = useState<number | null>(null)
  const top = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { user } = useAuth()
  const tutorial = tutorialById(id)

  if (!tutorial) {
    return (
      <>
        <PageHeader title="Tutorial" back={{ to: '/system/tutorials', label: 'Tutorials' }} />
        <EmptyState icon="book" title="There is no tutorial at this address">
          <Link to="/system/tutorials" className="font-semibold text-accent">
            See all tutorials
          </Link>
        </EmptyState>
      </>
    )
  }

  const total = tutorial.steps.length
  const index = Math.min(Math.max(Number(params.get('step')) || 1, 1), total) - 1
  const step = tutorial.steps[index]
  const next = TUTORIALS[TUTORIALS.indexOf(tutorial) + 1]

  function go(i: number) {
    setActive(null)
    setParams({ step: String(i + 1) })
    top.current?.scrollIntoView?.({ block: 'start' })
  }

  return (
    <div ref={top} className="scroll-mt-4">
      <PageHeader
        title={tutorial.title}
        subtitle={`${tutorial.feature} · ${total} steps · ${tutorial.summary}`}
        back={{ to: '/system/tutorials', label: 'Tutorials' }}
      />
      <StepList steps={tutorial.steps} index={index} onPick={go} />

      {/* Phone: step, legend, buttons, samples. Desktop: step and buttons left, the rest right. */}
      <div className="grid items-start gap-5 desk:grid-cols-[minmax(0,1fr)_300px]">
        <section
          aria-labelledby="tutorial-step-title"
          className="desk:col-start-1 desk:row-span-2 desk:row-start-1"
        >
          <Card className="p-4 desk:p-5">
            <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <p className="text-xs font-medium text-faint">
                Step {index + 1} of {total}
              </p>
              <StatusChip tone="draft">Signed in as {ROLE_LABELS[step.role]}</StatusChip>
            </div>
            <h2
              id="tutorial-step-title"
              className="text-lg font-semibold tracking-[-0.01em] text-ink"
            >
              {step.title}
            </h2>
            <p className="mt-1.5 mb-4 text-sm text-muted">{step.body}</p>
            <AnnotatedScreenshot step={step} active={active} onActive={setActive} />
            {step.tip && (
              <p className="mt-4 rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-[13px] text-muted">
                <b className="font-semibold text-ink">Tip · </b>
                {step.tip}
              </p>
            )}
          </Card>
        </section>

        <div className="desk:col-start-2 desk:row-start-1">
          <SidePanel title="On this screen">
            <div className="p-2">
              <Legend step={step} active={active} onActive={setActive} />
            </div>
            {step.path && canOpen(step.path, user?.role) && (
              <Link
                to={step.path}
                className="flex items-center gap-1 border-t border-line px-4 py-3 text-[13px] font-semibold text-accent hover:bg-surface-2"
              >
                Open this page
                <Icon name="chevron" strokeWidth={2} className="size-4" />
              </Link>
            )}
          </SidePanel>
        </div>

        <div className="-mt-4 desk:col-start-1 desk:row-start-3">
          <ButtonRow>
            <Button variant="ghost" disabled={index === 0} onClick={() => go(index - 1)}>
              Previous
            </Button>
            {index < total - 1 ? (
              <Button onClick={() => go(index + 1)}>Next</Button>
            ) : next ? (
              <Button onClick={() => navigate(`/system/tutorials/${next.id}`)}>
                Next tutorial: {next.feature}
              </Button>
            ) : (
              <Button onClick={() => navigate('/system/tutorials')}>All tutorials</Button>
            )}
          </ButtonRow>
        </div>

        <aside
          aria-label="Sample"
          className="grid gap-4 desk:col-start-2 desk:row-span-2 desk:row-start-2"
        >
          <SidePanel title="Sample data">
            <KeyValue items={tutorial.sample} />
          </SidePanel>
          {tutorial.files.length > 0 && <SampleFiles tutorial={tutorial} />}
        </aside>
      </div>
    </div>
  )
}
