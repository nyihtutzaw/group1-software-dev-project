import { useState } from 'react'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  SectionHeader,
  Select,
  StatTile,
  StatTiles,
  StatusChip,
  Textarea,
} from '@/components/ui'

import {
  type QueueItem,
  type Review,
  useAssign,
  useAssignableProjects,
  useDecide,
  useQueue,
  useReview,
  useSubmitReport,
  useVerifiers,
} from './api'
import { Checklist } from './Checklist'

function dueLabel(item: QueueItem) {
  const when = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(`${item.due_date}T00:00:00Z`))
  if (item.days_overdue === 0) return `Due ${when}`
  const days = item.days_overdue === 1 ? '1 day' : `${item.days_overdue} days`
  return `Due ${when} · ${days} overdue`
}

function QueueList({
  items,
  selected,
  showVerifier,
  onSelect,
}: {
  items: QueueItem[]
  selected: number | null
  showVerifier: boolean
  onSelect: (id: number) => void
}) {
  if (items.length === 0) {
    return (
      <EmptyState icon="verify" title="Nothing in the queue">
        Assigned projects will show here, oldest due date first.
      </EmptyState>
    )
  }
  return (
    <div className="grid gap-[11px]">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-current={selected === item.id ? 'true' : undefined}
          onClick={() => onSelect(item.id)}
          className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-line bg-surface px-3.5 py-3 text-left shadow-card hover:border-line-strong"
        >
          <span className="min-w-0">
            <b className="block truncate text-[15px]">{item.project_name}</b>
            <span className="mt-0.5 block font-mono text-xs text-faint">
              {item.project_code} · {dueLabel(item)}
              {showVerifier ? ` · ${item.verifier_name}` : ''}
            </span>
          </span>
          <StatusChip tone={item.chip_tone}>{item.chip}</StatusChip>
        </button>
      ))}
    </div>
  )
}

function AssignForm() {
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
        },
      },
    )
  }

  return (
    <section aria-label="Assign a verifier">
      <SectionHeader title="Assign a verifier" />
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
      {assign.isError && <Alert title="Could not assign">{assign.error.message}</Alert>}
      <ButtonRow>
        <Button
          disabled={!projectId || !verifierId || !dueDate || assign.isPending}
          onClick={submit}
        >
          {assign.isPending ? 'Assigning…' : 'Assign'}
        </Button>
      </ButtonRow>
    </section>
  )
}

function OpenReview({ id }: { id: number }) {
  const review = useReview(id)
  const submit = useSubmitReport(id)
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [note, setNote] = useState('')
  const [rationale, setRationale] = useState('')
  const [draftFor, setDraftFor] = useState<number | null>(null)

  if (review.isPending) return <p role="status">Loading review…</p>
  if (review.isError) {
    return (
      <Alert title="Unable to open this review">
        {review.error.message}
        <Button variant="ghost" onClick={() => void review.refetch()}>
          Try again
        </Button>
      </Alert>
    )
  }

  const data = review.data
  if (draftFor !== data.item.id) {
    setDraftFor(data.item.id)
    setChecked(Object.fromEntries(data.checklist.map((item) => [item.key, item.checked])))
    setNote(data.note)
    setRationale('')
  }

  return (
    <ReviewForm
      data={data}
      checked={checked}
      note={note}
      rationale={rationale}
      pending={submit.isPending}
      error={submit.isError ? submit.error.message : ''}
      onToggle={(key) => setChecked((current) => ({ ...current, [key]: !current[key] }))}
      onNote={setNote}
      onRationale={setRationale}
      onSubmit={(decision) =>
        submit.mutate({ checklist: checked, note, decision }, { onSuccess: () => setRationale('') })
      }
    />
  )
}

function ReviewForm({
  data,
  checked,
  note,
  rationale,
  pending,
  error,
  onToggle,
  onNote,
  onRationale,
  onSubmit,
}: {
  data: Review
  checked: Record<string, boolean>
  note: string
  rationale: string
  pending: boolean
  error: string
  onToggle: (key: string) => void
  onNote: (value: string) => void
  onRationale: (value: string) => void
  onSubmit: (decision: 'sign_off' | 'request_changes') => void
}) {
  const decide = useDecide(data.report_id ?? 0)

  return (
    <section aria-label={`Open review ${data.item.project_code}`}>
      <SectionHeader title={`Open review — ${data.item.project_code}`} />
      <Card className="mb-[11px] px-3.5 py-3">
        <p className="text-sm font-medium">Evidence</p>
        {data.evidence.map((line) => (
          <p key={line.title} className="mt-1 text-[13px] text-faint">
            <b className="font-medium text-muted">{line.title}.</b> {line.detail}
          </p>
        ))}
      </Card>
      <Card className="mb-[11px] px-3.5 py-3">
        <p className="text-sm font-medium">Automatic checks</p>
        {data.automatic_checks.map((check) => (
          <p key={check.name} className="mt-1 text-[13px] text-faint">
            <b className="font-medium text-muted">
              {check.name} · {check.passed ? 'clear' : 'needs attention'}.
            </b>{' '}
            {check.detail}
          </p>
        ))}
      </Card>
      <Card>
        <Checklist
          items={data.checklist}
          checked={checked}
          editable={data.can_submit}
          onToggle={onToggle}
        />
      </Card>
      <Card className="mt-[11px]">
        <Field label="Verifier note" htmlFor="verifier-note">
          <Textarea
            id="verifier-note"
            rows={2}
            value={note}
            disabled={!data.can_submit}
            placeholder="Visible to the developer and recorded in the ledger…"
            onChange={(event) => onNote(event.target.value)}
          />
        </Field>
      </Card>
      {data.can_submit && (
        <>
          {error && <Alert title="Could not submit">{error}</Alert>}
          <ButtonRow>
            <Button
              variant="ghost"
              disabled={pending || note.trim() === ''}
              onClick={() => onSubmit('request_changes')}
            >
              Request changes
            </Button>
            <Button disabled={pending || note.trim() === ''} onClick={() => onSubmit('sign_off')}>
              {pending ? 'Submitting…' : 'Sign off'}
            </Button>
          </ButtonRow>
          <p className="mt-2 text-center text-xs text-faint">
            Sign-off is irreversible and written to the audit ledger with your credential.
          </p>
        </>
      )}
      {data.decision_block && <Alert title="Someone else must decide">{data.decision_block}</Alert>}
      {data.can_decide && (
        <DecisionForm
          rationale={rationale}
          pending={decide.isPending}
          error={decide.isError ? decide.error.message : ''}
          onRationale={onRationale}
          onDecide={(decision) => decide.mutate({ decision, rationale })}
        />
      )}
      {data.approval && (
        <Alert
          tone={data.approval.decision === 'approved' ? 'ok' : 'warn'}
          title={`${data.approval.decision === 'approved' ? 'Approved' : 'Rejected'} by ${data.approval.approver_name}`}
        >
          {data.approval.rationale}
        </Alert>
      )}
      <SectionHeader title="Verification chain" />
      <Card className="px-3.5 py-1">
        {data.chain.map((event) => (
          <div key={event.id} className="border-b border-line py-3 last:border-b-0">
            <b className="block text-sm font-medium">{event.summary}</b>
            <span className="mt-0.5 block font-mono text-xs text-faint">
              {event.actor_name} ·{' '}
              {new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' }).format(
                new Date(event.at),
              )}
            </span>
            {event.note && <p className="mt-1 text-[13px] text-muted">{event.note}</p>}
          </div>
        ))}
      </Card>
    </section>
  )
}

function DecisionForm({
  rationale,
  pending,
  error,
  onRationale,
  onDecide,
}: {
  rationale: string
  pending: boolean
  error: string
  onRationale: (value: string) => void
  onDecide: (decision: 'approved' | 'rejected') => void
}) {
  return (
    <>
      <Card className="mt-[11px]">
        <Field label="Rationale" htmlFor="approval-rationale" hint="Recorded with the decision.">
          <Textarea
            id="approval-rationale"
            rows={2}
            value={rationale}
            placeholder="Why this sign-off is approved or rejected"
            onChange={(event) => onRationale(event.target.value)}
          />
        </Field>
      </Card>
      {error && <Alert title="Could not record the decision">{error}</Alert>}
      <ButtonRow>
        <Button
          variant="danger"
          disabled={pending || rationale.trim().length < 5}
          onClick={() => onDecide('rejected')}
        >
          Reject
        </Button>
        <Button
          disabled={pending || rationale.trim().length < 5}
          onClick={() => onDecide('approved')}
        >
          {pending ? 'Saving…' : 'Approve'}
        </Button>
      </ButtonRow>
    </>
  )
}

export function VerifyPage() {
  const { user } = useAuth()
  const queue = useQueue()
  const [selected, setSelected] = useState<number | null>(null)
  const staff = user?.role === 'registry_staff' || user?.role === 'admin'
  const items = queue.data?.items ?? []
  const openId = selected ?? items[0]?.id ?? null

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
          <SectionHeader title="Queue" action={<span>Sort: oldest</span>} />
          <QueueList items={items} selected={openId} showVerifier={staff} onSelect={setSelected} />
          {openId !== null && <OpenReview id={openId} />}
        </>
      )}
      {staff && <AssignForm />}
    </>
  )
}
