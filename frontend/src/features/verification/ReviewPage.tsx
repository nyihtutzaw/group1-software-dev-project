import { useState } from 'react'
import { useParams } from 'react-router'

import {
  Alert,
  Button,
  ButtonRow,
  Card,
  Field,
  Icon,
  KeyValue,
  PageHeader,
  SectionHeader,
  StatusChip,
  TabPanel,
  Tabs,
  Textarea,
} from '@/components/ui'
import { cn } from '@/lib/cn'

import { type Review, useDecide, useReview, useSubmitReport } from './api'
import { Checklist } from './Checklist'
import { dueLabel, longDate, overdueLabel } from './format'

type Tab = 'review' | 'evidence' | 'history'

const BACK = { to: '/verify', label: 'Verification queue' }

/** One assignment: the verifier's checklist and sign-off, staff's decision, evidence and history. */
export function ReviewPage() {
  const id = Number(useParams().id)
  const review = useReview(Number.isInteger(id) ? id : null)

  if (review.isPending) {
    return (
      <>
        <PageHeader title="Review" back={BACK} />
        <p role="status">Loading review…</p>
      </>
    )
  }
  if (review.isError) {
    return (
      <>
        <PageHeader title="Review" back={BACK} />
        <Alert title="Unable to open this review">
          {review.error.message}
          <Button variant="ghost" className="mt-2" onClick={() => void review.refetch()}>
            Try again
          </Button>
        </Alert>
      </>
    )
  }
  return <ReviewBody key={review.data.item.id} data={review.data} />
}

function ReviewBody({ data }: { data: Review }) {
  const { item } = data
  const submit = useSubmitReport(item.id)
  const decide = useDecide(data.report_id ?? 0)
  const [tab, setTab] = useState<Tab>('review')
  const [checked, setChecked] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(data.checklist.map((line) => [line.key, line.checked])),
  )
  const [note, setNote] = useState(data.note)
  const [rationale, setRationale] = useState('')
  const done = data.checklist.filter((line) => checked[line.key]).length
  const failing = data.automatic_checks.filter((check) => !check.passed).length

  return (
    <section aria-label={`Open review ${item.project_code}`}>
      <PageHeader
        back={BACK}
        title={item.project_name}
        subtitle={
          <>
            <span className="font-mono">{item.project_code}</span> · {dueLabel(item)}
          </>
        }
        actions={<StatusChip tone={item.chip_tone}>{item.chip}</StatusChip>}
      />

      <div className="grid gap-6 desk:grid-cols-[minmax(0,1fr)_280px] desk:items-start">
        <div className="min-w-0">
          <Tabs
            idBase="review"
            label="Review sections"
            value={tab}
            onChange={setTab}
            tabs={[
              { id: 'review', label: 'Review' },
              { id: 'evidence', label: 'Evidence & checks', count: data.evidence.length },
              { id: 'history', label: 'History', count: data.chain.length },
            ]}
          />
          <TabPanel idBase="review" id={tab}>
            {tab === 'review' && (
              <>
                {data.approval && (
                  <Alert
                    className="mb-4"
                    tone={data.approval.decision === 'approved' ? 'ok' : 'warn'}
                    title={`${data.approval.decision === 'approved' ? 'Approved' : 'Rejected'} by ${data.approval.approver_name}`}
                  >
                    {data.approval.rationale}
                  </Alert>
                )}
                {data.decision_block && (
                  <Alert className="mb-4" title="Someone else must decide">
                    {data.decision_block}
                  </Alert>
                )}
                <SectionHeader
                  title="Checklist"
                  action={
                    <span className="font-medium text-faint">
                      {done} of {data.checklist.length} confirmed
                    </span>
                  }
                />
                <Card className="overflow-hidden">
                  <Checklist
                    items={data.checklist}
                    checked={checked}
                    editable={data.can_submit}
                    onToggle={(key) =>
                      setChecked((current) => ({ ...current, [key]: !current[key] }))
                    }
                  />
                </Card>
                <Card className="mt-3">
                  <Field label="Verifier note" htmlFor="verifier-note">
                    <Textarea
                      id="verifier-note"
                      rows={3}
                      value={note}
                      disabled={!data.can_submit}
                      placeholder="Visible to the developer and recorded in the ledger…"
                      onChange={(event) => setNote(event.target.value)}
                    />
                  </Field>
                </Card>
                {data.can_submit && (
                  <>
                    {submit.isError && (
                      <Alert className="mt-3" title="Could not submit">
                        {submit.error.message}
                      </Alert>
                    )}
                    <ButtonRow>
                      <Button
                        variant="ghost"
                        disabled={submit.isPending || note.trim() === ''}
                        onClick={() =>
                          submit.mutate({ checklist: checked, note, decision: 'request_changes' })
                        }
                      >
                        Request changes
                      </Button>
                      <Button
                        disabled={submit.isPending || note.trim() === ''}
                        onClick={() =>
                          submit.mutate({ checklist: checked, note, decision: 'sign_off' })
                        }
                      >
                        {submit.isPending ? 'Submitting…' : 'Sign off'}
                      </Button>
                    </ButtonRow>
                    <p className="mt-2 text-center text-xs text-faint">
                      Sign-off is irreversible and written to the audit ledger with your credential.
                    </p>
                  </>
                )}
                {data.can_decide && (
                  <>
                    <SectionHeader title="Decision" />
                    <Card>
                      <Field
                        label="Rationale"
                        htmlFor="approval-rationale"
                        hint="Recorded with the decision. At least 5 characters."
                      >
                        <Textarea
                          id="approval-rationale"
                          rows={3}
                          value={rationale}
                          placeholder="Why this sign-off is approved or rejected"
                          onChange={(event) => setRationale(event.target.value)}
                        />
                      </Field>
                    </Card>
                    {decide.isError && (
                      <Alert className="mt-3" title="Could not record the decision">
                        {decide.error.message}
                      </Alert>
                    )}
                    <ButtonRow>
                      <Button
                        variant="danger"
                        disabled={decide.isPending || rationale.trim().length < 5}
                        onClick={() => decide.mutate({ decision: 'rejected', rationale })}
                      >
                        Reject
                      </Button>
                      <Button
                        disabled={decide.isPending || rationale.trim().length < 5}
                        onClick={() => decide.mutate({ decision: 'approved', rationale })}
                      >
                        {decide.isPending ? 'Saving…' : 'Approve'}
                      </Button>
                    </ButtonRow>
                  </>
                )}
              </>
            )}

            {tab === 'evidence' && (
              <>
                <SectionHeader title="Evidence" />
                <Card className="overflow-hidden">
                  <ul>
                    {data.evidence.map((line, index) => (
                      <li
                        key={`${index}-${line.title}`}
                        className="flex gap-3 border-b border-line px-4 py-3 last:border-b-0"
                      >
                        <Icon name="file" className="mt-0.5 size-4 flex-none text-faint" />
                        <span className="min-w-0">
                          <b className="block text-sm font-medium">{line.title}</b>
                          <span className="mt-0.5 block text-[13px] wrap-anywhere text-faint">
                            {line.detail}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </Card>
                <SectionHeader title="Automatic checks" />
                <Card className="overflow-hidden">
                  <ul>
                    {data.automatic_checks.map((check) => (
                      <li
                        key={check.name}
                        className="flex items-start justify-between gap-3 border-b border-line px-4 py-3 last:border-b-0"
                      >
                        <span className="min-w-0">
                          <b className="block text-sm font-medium">{check.name}</b>
                          <span className="mt-0.5 block text-[13px] text-faint">
                            {check.detail}
                          </span>
                        </span>
                        <StatusChip tone={check.passed ? 'ok' : 'warn'}>
                          {check.passed ? 'CLEAR' : 'NEEDS ATTENTION'}
                        </StatusChip>
                      </li>
                    ))}
                  </ul>
                </Card>
              </>
            )}

            {tab === 'history' && (
              <Card className="px-4 py-1">
                <ol>
                  {data.chain.map((event) => (
                    <li
                      key={event.id}
                      className="relative border-b border-line py-3 pl-6 last:border-b-0"
                    >
                      <span
                        className={cn(
                          'absolute top-[18px] left-0 size-2.5 rounded-full',
                          event.kind === 'approval'
                            ? 'bg-ok'
                            : event.kind === 'report'
                              ? 'bg-accent'
                              : 'bg-line-strong',
                        )}
                        aria-hidden="true"
                      />
                      <b className="block text-sm font-medium">{event.summary}</b>
                      <span className="mt-0.5 block text-xs text-faint">
                        {event.actor_name} · {longDate(event.at)}
                      </span>
                      {event.note && <p className="mt-1 text-[13px] text-muted">{event.note}</p>}
                    </li>
                  ))}
                </ol>
              </Card>
            )}
          </TabPanel>
        </div>

        <aside aria-label="Summary" className="grid gap-3 desk:sticky desk:top-24">
          <Card className="overflow-hidden">
            <p className="border-b border-line px-4 py-3 text-sm font-semibold">Summary</p>
            <KeyValue
              items={[
                { label: 'Project', value: item.project_code, mono: true },
                { label: 'Verifier', value: item.verifier_name },
                { label: 'Due', value: longDate(item.due_date) },
                ...(overdueLabel(item)
                  ? [
                      {
                        label: 'Overdue',
                        value: <span className="text-warn">{overdueLabel(item)}</span>,
                      },
                    ]
                  : []),
                { label: 'Checklist', value: `${done} / ${data.checklist.length}` },
                {
                  label: 'Auto checks',
                  value:
                    failing === 0 ? (
                      <span className="text-ok">All clear</span>
                    ) : (
                      <span className="text-warn">{failing} need attention</span>
                    ),
                },
              ]}
            />
          </Card>
        </aside>
      </div>
    </section>
  )
}
