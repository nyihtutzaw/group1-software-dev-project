import { useState } from 'react'
import { Link } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Field,
  Icon,
  Input,
  PageHeader,
  Select,
  StatTile,
  StatTiles,
  StatusChip,
  TabPanel,
  Tabs,
} from '@/components/ui'
import { cn } from '@/lib/cn'

import { type QueueItem, useAssign, useAssignableProjects, useQueue, useVerifiers } from './api'
import { groupOf, overdueLabel, type QueueGroup, shortDate } from './format'

type Tab = QueueGroup | 'assign'

const EMPTY: Record<QueueGroup, { title: string; body: string }> = {
  open: {
    title: 'Nothing in progress',
    body: 'Assigned projects waiting for a verifier report show here, oldest due date first.',
  },
  awaiting: {
    title: 'Nothing awaiting approval',
    body: 'Verifier sign-offs waiting for a registry staff decision show here.',
  },
  approved: {
    title: 'Nothing approved yet',
    body: 'Approved verifications show here once registry staff sign them off.',
  },
}

function QueueTable({ items, showVerifier }: { items: QueueItem[]; showVerifier: boolean }) {
  const cols = showVerifier
    ? 'desk:grid-cols-[minmax(0,1fr)_170px_150px_140px_16px]'
    : 'desk:grid-cols-[minmax(0,1fr)_150px_140px_16px]'
  return (
    <Card className="overflow-hidden">
      <div
        className={cn(
          'hidden gap-4 border-b border-line bg-surface-2 px-4 py-2.5 text-xs font-medium text-faint desk:grid',
          cols,
        )}
        aria-hidden="true"
      >
        <span>Project</span>
        {showVerifier && <span>Verifier</span>}
        <span>Due</span>
        <span>Status</span>
        <span />
      </div>
      <ul>
        {items.map((item) => {
          const overdue = overdueLabel(item)
          return (
            <li key={item.id} className="border-b border-line last:border-b-0">
              <Link
                to={`/verify/${item.id}`}
                className={cn(
                  'grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-3 transition-colors hover:bg-surface-2',
                  cols,
                )}
              >
                <span className="min-w-0">
                  <b className="block truncate text-sm font-semibold">{item.project_name}</b>
                  <span className="mt-0.5 block truncate text-xs text-faint">
                    <span className="font-mono">{item.project_code}</span>
                    <span className="desk:hidden">
                      {' · '}Due {shortDate(item.due_date)}
                      {overdue && ` · ${overdue}`}
                      {showVerifier && ` · ${item.verifier_name}`}
                    </span>
                  </span>
                </span>
                {showVerifier && (
                  <span className="hidden truncate text-sm text-muted desk:block">
                    {item.verifier_name}
                  </span>
                )}
                <span className="hidden text-sm desk:block">
                  <span className="block text-ink">{shortDate(item.due_date)}</span>
                  {overdue && <span className="block text-xs text-warn">{overdue}</span>}
                </span>
                <span>
                  <StatusChip tone={item.chip_tone}>{item.chip}</StatusChip>
                </span>
                <Icon
                  name="chevron"
                  strokeWidth={2}
                  className="hidden size-4 text-faint desk:block"
                />
              </Link>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

function AssignForm({ onAssigned }: { onAssigned: () => void }) {
  const projects = useAssignableProjects(true)
  const verifiers = useVerifiers(true)
  const assign = useAssign()
  const [projectId, setProjectId] = useState('')
  const [verifierId, setVerifierId] = useState('')
  const [dueDate, setDueDate] = useState('')

  function submit() {
    assign.mutate(
      { project_id: Number(projectId), verifier_id: Number(verifierId), due_date: dueDate },
      {
        onSuccess: () => {
          setProjectId('')
          setVerifierId('')
          setDueDate('')
          onAssigned()
        },
      },
    )
  }

  return (
    <section aria-label="Assign a verifier" className="max-w-xl">
      <p className="mb-4 text-sm text-faint">
        Only submitted projects can be assigned. The verifier reviews the evidence and signs off; a
        different registry staff member then approves or rejects.
      </p>
      <Card>
        <Field label="Project" htmlFor="assign-project">
          <Select
            id="assign-project"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
          >
            <option value="">Choose a project</option>
            {projects.data?.map((project) => (
              <option key={project.id} value={project.id}>
                {project.code} · {project.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Verifier" htmlFor="assign-verifier">
          <Select
            id="assign-verifier"
            value={verifierId}
            onChange={(event) => setVerifierId(event.target.value)}
          >
            <option value="">Choose a verifier</option>
            {verifiers.data?.map((verifier) => (
              <option key={verifier.id} value={verifier.id}>
                {verifier.full_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Due date" htmlFor="assign-due">
          <Input
            id="assign-due"
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
          />
        </Field>
      </Card>
      {assign.isError && (
        <Alert className="mt-3" title="Could not assign">
          {assign.error.message}
        </Alert>
      )}
      <div className="mt-4 flex justify-end">
        <div className="w-full min-[421px]:w-40">
          <Button
            disabled={!projectId || !verifierId || !dueDate || assign.isPending}
            onClick={submit}
          >
            {assign.isPending ? 'Assigning…' : 'Assign'}
          </Button>
        </div>
      </div>
    </section>
  )
}

export function VerifyPage() {
  const { user } = useAuth()
  const queue = useQueue()
  const [picked, setPicked] = useState<Tab | null>(null)
  const staff = user?.role === 'registry_staff' || user?.role === 'admin'
  const items = queue.data?.items ?? []
  const groups: Record<QueueGroup, QueueItem[]> = { open: [], awaiting: [], approved: [] }
  for (const item of items) groups[groupOf(item.status)].push(item)
  // Staff start where their decision is needed; verifiers on their open work
  const tab: Tab = picked ?? (staff && groups.awaiting.length > 0 ? 'awaiting' : 'open')

  const subtitle = queue.data
    ? staff
      ? `${queue.data.assigned_count} assignments · ${queue.data.overdue_count} overdue`
      : `${queue.data.assigned_count} assigned to you · ${queue.data.overdue_count} overdue`
    : 'Projects assigned for review'

  return (
    <>
      <PageHeader title="Verification queue" subtitle={subtitle} />
      {queue.isPending && <p role="status">Loading queue…</p>}
      {queue.isError && (
        <Alert title="Unable to load the queue">
          {queue.error.message}
          <Button variant="ghost" onClick={() => void queue.refetch()}>
            Try again
          </Button>
        </Alert>
      )}
      {queue.data && (
        <>
          <StatTiles>
            <StatTile value={queue.data.assigned_count} label="Assigned" tone="accent" />
            <StatTile value={queue.data.overdue_count} label="Overdue" tone="warn" />
            <StatTile
              value={queue.data.signed_off_this_year}
              label="Signed off this year"
              tone="ok"
            />
          </StatTiles>
          <Tabs
            className="mt-8"
            idBase="queue"
            label="Verification queue"
            value={tab}
            onChange={setPicked}
            tabs={[
              { id: 'open', label: 'In progress', count: groups.open.length },
              { id: 'awaiting', label: 'Awaiting approval', count: groups.awaiting.length },
              { id: 'approved', label: 'Approved', count: groups.approved.length },
              ...(staff ? [{ id: 'assign' as const, label: 'Assign verifier' }] : []),
            ]}
          />
          <TabPanel idBase="queue" id={tab}>
            {tab === 'assign' ? (
              <AssignForm onAssigned={() => setPicked('open')} />
            ) : groups[tab].length === 0 ? (
              <EmptyState icon="verify" title={EMPTY[tab].title}>
                {EMPTY[tab].body}
              </EmptyState>
            ) : (
              <QueueTable items={groups[tab]} showVerifier={staff} />
            )}
          </TabPanel>
        </>
      )}
    </>
  )
}
