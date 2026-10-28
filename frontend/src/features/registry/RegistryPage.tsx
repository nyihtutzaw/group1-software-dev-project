import { useState } from 'react'
import { Link } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Field,
  Input,
  KeyValue,
  PageHeader,
  SectionHeader,
  StatusChip,
} from '@/components/ui'
import { api } from '@/lib/api'

import { type Credit, type EvidencePack, type Integrity, useCredit, useCredits } from './api'

function date(value: string) {
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(value),
  )
}

function CreditStatus({ status }: { status: Credit['status'] }) {
  return (
    <StatusChip tone={status === 'active' ? 'ok' : status === 'revoked' ? 'warn' : 'draft'}>
      {status}
    </StatusChip>
  )
}

function Traceability({ id }: { id: number }) {
  const { user } = useAuth()
  const detail = useCredit(id)
  const [pack, setPack] = useState<EvidencePack | null>(null)
  const [integrity, setIntegrity] = useState<Integrity | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState<'evidence' | 'integrity' | null>(null)
  const mayReadEvidence = user && ['buyer', 'registry_staff', 'admin'].includes(user.role)

  async function load(action: 'evidence' | 'integrity') {
    setPending(action)
    setError('')
    try {
      if (action === 'evidence') {
        setPack(await api.get<EvidencePack>(`/registry/credits/${id}/evidence`))
      } else {
        setIntegrity(await api.get<Integrity>(`/registry/credits/${id}/integrity`))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load this record. Please try again.')
    } finally {
      setPending(null)
    }
  }

  if (detail.isPending) return <p role="status">Loading traceability…</p>
  if (detail.isError)
    return (
      <Alert title="Unable to load traceability">
        {detail.error.message}
        <Button variant="ghost" onClick={() => void detail.refetch()}>
          Try again
        </Button>
      </Alert>
    )
  const credit = detail.data

  return (
    <section aria-label="Credit traceability">
      <SectionHeader title={`Traceability — ${credit.project_reference}`} />
      <Card>
        <KeyValue
          items={[
            { label: 'Project', value: credit.project_name },
            { label: 'Country', value: credit.country },
            { label: 'Serial', value: credit.serial, mono: true },
            { label: 'Vintage', value: credit.vintage, mono: true },
            { label: 'Quantity', value: `${credit.quantity.toLocaleString()} tCO₂e` },
            { label: 'Methodology', value: credit.methodology },
            { label: 'Verifier', value: credit.verifier_name },
            { label: 'Verification status', value: credit.verification_status },
            { label: 'Verification', value: credit.verification_reference, mono: true },
            { label: 'Signed off', value: date(credit.signed_off_at), mono: true },
            { label: 'Approval', value: credit.approval_reference, mono: true },
            { label: 'Issued', value: date(credit.issued_at), mono: true },
            { label: 'Status', value: <CreditStatus status={credit.status} /> },
            { label: 'Monitoring', value: 'Not available — monitoring is deferred' },
            { label: 'Audit ledger', value: 'Not available — ledger not connected' },
          ]}
        />
      </Card>
      <ButtonRow>
        <Button
          variant="ghost"
          disabled={!mayReadEvidence || pending !== null}
          onClick={() => void load('evidence')}
        >
          {pending === 'evidence' ? 'Loading evidence…' : 'Evidence pack'}
        </Button>
        <Button disabled={pending !== null} onClick={() => void load('integrity')}>
          {pending === 'integrity' ? 'Checking…' : 'Verify authenticity'}
        </Button>
      </ButtonRow>
      <p className="mt-2 text-center text-xs text-faint">
        {!user ? (
          <>
            <Link className="text-accent underline" to="/login">
              Sign in as an authorised buyer
            </Link>{' '}
            to view permitted evidence summaries.
          </>
        ) : !mayReadEvidence ? (
          'Evidence packs require buyer, registry staff or admin access.'
        ) : (
          'Evidence packs contain reviewed buyer-safe summaries. Original files are not exposed.'
        )}
      </p>
      {error && (
        <Alert className="mt-3" title="Request failed">
          {error}
        </Alert>
      )}
      {integrity && (
        <Alert
          className="mt-3"
          tone={integrity.snapshot_matches ? 'ok' : 'warn'}
          title={
            integrity.snapshot_matches
              ? 'Publication snapshot matches'
              : 'Publication snapshot mismatch'
          }
        >
          {integrity.notice}
        </Alert>
      )}
      {pack && (
        <section aria-label="Evidence pack">
          <SectionHeader title="Evidence pack" />
          <p className="mb-3 text-sm text-faint">{pack.notice}</p>
          {pack.items.length === 0 ? (
            <EmptyState icon="registry" title="No permitted evidence">
              No reviewed evidence summaries are available for this credit.
            </EmptyState>
          ) : (
            <div className="space-y-3">
              {pack.items.map((item) => (
                <Card key={item.id} className="p-3.5">
                  <h4 className="font-semibold">{item.title}</h4>
                  <p className="mt-1 text-sm whitespace-pre-wrap text-muted">{item.summary}</p>
                </Card>
              ))}
            </div>
          )}
        </section>
      )}
      <SectionHeader title="Credit history" />
      <Card>
        <ol className="divide-y divide-line">
          {credit.history.map((event, index) => (
            <li
              key={`${event.action}-${index}`}
              className="flex justify-between gap-3 p-3.5 text-sm"
            >
              <span className="capitalize">{event.action}</span>
              <time dateTime={event.occurred_at} className="font-mono text-faint">
                {date(event.occurred_at)}
              </time>
            </li>
          ))}
        </ol>
      </Card>
    </section>
  )
}

export function RegistryPage() {
  const { user } = useAuth()
  const [input, setInput] = useState('')
  const [q, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<number | null>(null)
  const credits = useCredits(q, page)
  const scope = `${user?.id ?? 'public'}-${user?.role ?? 'public'}`
  // Selection is only valid within the current visible page and session scope.
  const selectedId = credits.data?.items.some((item) => item.id === selected) ? selected : null

  return (
    <>
      <PageHeader
        title="Public registry"
        subtitle="Every issued credit, traceable to the evidence behind it"
      />
      {user?.role === 'buyer' && (
        <p className="mb-3 text-sm text-muted">Showing projects you are permitted to access.</p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(input.trim())
          setPage(1)
          setSelected(null)
        }}
        className="flex items-center gap-3"
      >
        <Card className="min-w-0 flex-1">
          <Field label="Search project, serial or country" htmlFor="registry-search">
            <Input
              id="registry-search"
              value={input}
              maxLength={200}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Search project, serial or country"
            />
          </Field>
        </Card>
        <div className="w-24 shrink-0">
          <Button type="submit">Search</Button>
        </div>
      </form>
      <section aria-label="Registry results" aria-busy={credits.isFetching}>
        <SectionHeader
          title={
            credits.data
              ? `${credits.data.total} ${credits.data.total === 1 ? 'result' : 'results'}`
              : 'Issued credits'
          }
          action="Vintage ↓"
        />
        {credits.isPending && <p role="status">Loading credits…</p>}
        {credits.isError && (
          <Alert title="Unable to load credits">
            {credits.error.message}
            <Button variant="ghost" onClick={() => void credits.refetch()}>
              Try again
            </Button>
          </Alert>
        )}
        {credits.data &&
          (credits.data.items.length === 0 ? (
            <EmptyState
              icon="registry"
              title={q ? 'No matching credits' : 'No issued credits available'}
            >
              {q
                ? 'Try another project name, serial or country.'
                : user?.role === 'buyer'
                  ? 'No published credits are available for your permitted projects.'
                  : 'Credits appear here once approved records are published.'}
            </EmptyState>
          ) : (
            <>
              <div className="space-y-3">
                {credits.data.items.map((credit) => (
                  <Card key={credit.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(credit.id)}
                      aria-pressed={selectedId === credit.id}
                      className="w-full rounded-xl p-3.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold">{credit.project_name}</span>
                        <CreditStatus status={credit.status} />
                      </div>
                      <p className="mt-1 font-mono text-xs wrap-anywhere text-muted">
                        {credit.serial}
                      </p>
                      <p className="mt-2 text-sm text-faint">
                        {credit.country} · Vintage {credit.vintage} ·{' '}
                        {credit.quantity.toLocaleString()} tCO₂e
                      </p>
                    </button>
                  </Card>
                ))}
              </div>
              <nav
                aria-label="Registry pagination"
                className="mt-3 flex items-center justify-between gap-3"
              >
                <div className="w-24 shrink-0">
                  <Button
                    variant="ghost"
                    disabled={page === 1}
                    onClick={() => {
                      setPage(page - 1)
                      setSelected(null)
                    }}
                  >
                    Previous
                  </Button>
                </div>
                <span className="text-sm whitespace-nowrap text-faint">
                  Page {page} of {Math.ceil(credits.data.total / credits.data.page_size)}
                </span>
                <div className="w-24 shrink-0">
                  <Button
                    variant="ghost"
                    disabled={page * credits.data.page_size >= credits.data.total}
                    onClick={() => {
                      setPage(page + 1)
                      setSelected(null)
                    }}
                  >
                    Next
                  </Button>
                </div>
              </nav>
            </>
          ))}
      </section>
      {selectedId !== null && <Traceability key={`${scope}-${selectedId}`} id={selectedId} />}
    </>
  )
}
