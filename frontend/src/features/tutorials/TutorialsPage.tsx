import { Link } from 'react-router'

import { ROLE_LABELS } from '@/auth/types'
import { Alert, Card, Icon, PageHeader, StatusChip } from '@/components/ui'

import { TUTORIALS } from './content'
import { DownloadManual } from './DownloadManual'
import type { Tutorial } from './types'

function TutorialCard({ tutorial }: { tutorial: Tutorial }) {
  const cover = tutorial.steps[0]
  return (
    <li>
      <Link
        to={`/system/tutorials/${tutorial.id}`}
        className="group block h-full rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <Card className="flex h-full flex-col overflow-hidden transition-shadow group-hover:shadow-lg">
          <div className="aspect-[16/8] overflow-hidden border-b border-line bg-surface-2">
            <img
              src={cover.image}
              alt=""
              loading="lazy"
              className="size-full object-cover object-top transition-transform duration-300 group-hover:scale-[1.02]"
            />
          </div>
          <div className="flex flex-1 flex-col gap-2 p-4">
            <div className="flex items-center gap-2">
              <span className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent">
                <Icon name={tutorial.icon} className="size-[18px]" />
              </span>
              <StatusChip tone="accent">{tutorial.feature}</StatusChip>
              <span className="ml-auto text-xs text-faint">{tutorial.steps.length} steps</span>
            </div>
            <h2 className="text-[15px] font-semibold text-ink">{tutorial.title}</h2>
            <p className="text-[13px] text-muted">{tutorial.summary}</p>
            <p className="text-xs text-faint">
              For: {tutorial.roles.map((r) => ROLE_LABELS[r]).join(', ')}
            </p>
            <span className="mt-auto inline-flex items-center gap-1 pt-2 text-[13px] font-semibold text-accent">
              Start walkthrough
              <Icon name="chevron" strokeWidth={2} className="size-4" />
            </span>
          </div>
        </Card>
      </Link>
    </li>
  )
}

/** System › Tutorials — one step-by-step walkthrough per feature. */
export function TutorialsPage() {
  return (
    <>
      <PageHeader
        title="Tutorials"
        subtitle="Step-by-step walkthroughs of every feature, with annotated screenshots"
        actions={<DownloadManual />}
      />
      <Alert tone="ok" icon="book" title="One sample project, start to finish">
        Every walkthrough follows the same fictional project, “Nam Wa Hillside Reforestation”, from
        registration to a retired credit. Each one lists the sample values and files it uses, so you
        can repeat the steps yourself.
      </Alert>
      <ol aria-label="Tutorials" className="mt-6 grid gap-4 desk:grid-cols-2">
        {TUTORIALS.map((t) => (
          <TutorialCard key={t.id} tutorial={t} />
        ))}
      </ol>
    </>
  )
}
