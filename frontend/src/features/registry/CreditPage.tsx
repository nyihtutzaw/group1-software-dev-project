import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  Card,
  EmptyState,
  KeyValue,
  Modal,
  PageHeader,
  SectionHeader,
} from '@/components/ui'
import { api } from '@/lib/api'

import { type CreditDetail, type EvidencePack, type Integrity, useCredit } from './api'
import { CreditStatus } from './CreditStatus'
import { date } from './format'

/** One credit's traceability: origin, verification, approval, history, evidence and integrity. */
export function CreditPage() {
  const { user } = useAuth()
  const id = Number(useParams().id)
  const from = (useLocation().state as { from?: string } | null)?.from
  const back = { to: from ?? '/registry', label: 'Public registry' }
  const detail = useCredit(Number.isInteger(id) ? id : null)
  // Evidence and integrity results belong to one signed-in user
  const scope = `${user?.id ?? 'public'}-${user?.role ?? 'public'}-${id}`

  if (detail.isPending) {
    return (
      <>
        <PageHeader title="Credit" back={back} />
        <p role="status">Loading traceability…</p>
      </>
    )
  }
  if (detail.isError) {
    return (
      <>
        <PageHeader title="Credit" back={back} />
        <Alert title="Unable to load traceability">
          {detail.error.message}
          <Button variant="ghost" className="mt-2" onClick={() => void detail.refetch()}>
            Try again
          </Button>
        </Alert>
      </>
    )
  }
  return <CreditBody key={scope} credit={detail.data} back={back} />
}

function CreditBody({
  credit,
  back,
}: {
  credit: CreditDetail
  back: { to: string; label: string }
}) {
  const { user } = useAuth()
  const [pack, setPack] = useState<EvidencePack | null>(null)
  const [packOpen, setPackOpen] = useState(false)
  const [integrity, setIntegrity] = useState<Integrity | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState<'evidence' | 'integrity' | null>(null)
  const mayReadEvidence = user && ['buyer', 'registry_staff', 'admin'].includes(user.role)
  const closePack = useCallback(() => setPackOpen(false), [])

  async function load(action: 'evidence' | 'integrity') {
    setPending(action)
    setError('')
    try {
      if (action === 'evidence') {
        setPack(await api.get<EvidencePack>(`/registry/credits/${credit.id}/evidence`))
        setPackOpen(true)
      } else {
        setIntegrity(await api.get<Integrity>(`/registry/credits/${credit.id}/integrity`))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load this record. Please try again.')
    } finally {
      setPending(null)
    }
  }

  return (
    <section aria-label="Credit traceability">
      <PageHeader
        back={back}
        title={credit.project_name}
        subtitle={
          <>
            <span className="font-mono">{credit.serial}</span> · {credit.project_reference}
          </>
        }
        actions={<CreditStatus status={credit.status} />}
      />

      <div className="grid gap-6 desk:grid-cols-[minmax(0,1fr)_300px] desk:items-start">
        <div className="min-w-0">
          <SectionHeader title="Origin" />
          <Card className="overflow-hidden">
            <KeyValue
              items={[
                { label: 'Project', value: credit.project_name },
                { label: 'Reference', value: credit.project_reference, mono: true },
                { label: 'Country', value: credit.country },
                { label: 'Methodology', value: credit.methodology },
                { label: 'Vintage', value: credit.vintage, mono: true },
                { label: 'Quantity', value: `${credit.quantity.toLocaleString()} tCO₂e` },
              ]}
            />
          </Card>
          <SectionHeader title="Verification & approval" />
          <Card className="overflow-hidden">
            <KeyValue
              items={[
                { label: 'Verifier', value: credit.verifier_name },
                { label: 'Verification status', value: credit.verification_status },
                { label: 'Verification', value: credit.verification_reference, mono: true },
                { label: 'Signed off', value: date(credit.signed_off_at) },
                { label: 'Approval', value: credit.approval_reference, mono: true },
                { label: 'Issued', value: date(credit.issued_at) },
                { label: 'Monitoring', value: 'Not available — monitoring is deferred' },
                { label: 'Audit ledger', value: 'Not available — ledger not connected' },
              ]}
            />
          </Card>
          <SectionHeader title="Credit history" />
          <Card className="overflow-hidden">
            <ol>
              {credit.history.map((event, index) => (
                <li
                  key={`${event.action}-${index}`}
                  className="flex justify-between gap-3 border-b border-line px-4 py-3 text-sm last:border-b-0"
                >
                  <span className="capitalize">{event.action}</span>
                  <time dateTime={event.occurred_at} className="text-faint">
                    {date(event.occurred_at)}
                  </time>
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <aside aria-label="Check this credit" className="grid gap-3 desk:sticky desk:top-24">
          <Card className="p-4">
            <p className="text-sm font-semibold">Check this credit</p>
            <p className="mt-1 text-[13px] text-faint">
              Compare the published record with its stored fingerprint, or read the reviewed
              evidence behind it.
            </p>
            <div className="mt-4 grid gap-2.5">
              <Button disabled={pending !== null} onClick={() => void load('integrity')}>
                {pending === 'integrity' ? 'Checking…' : 'Verify authenticity'}
              </Button>
              <Button
                variant="ghost"
                disabled={!mayReadEvidence || pending !== null}
                onClick={() => void load('evidence')}
              >
                {pending === 'evidence' ? 'Loading evidence…' : 'Evidence pack'}
              </Button>
            </div>
            <p className="mt-3 text-xs text-faint">
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
          </Card>
          {error && <Alert title="Request failed">{error}</Alert>}
          {integrity && (
            <Alert
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
        </aside>
      </div>

      <Modal open={packOpen && pack !== null} title="Evidence pack" onClose={closePack}>
        {pack && (
          <>
            {pack.notice && <p className="mb-3 text-sm text-faint">{pack.notice}</p>}
            {pack.items.length === 0 ? (
              <EmptyState icon="registry" title="No permitted evidence">
                No reviewed evidence summaries are available for this credit.
              </EmptyState>
            ) : (
              <div className="grid gap-3">
                {pack.items.map((item) => (
                  <Card key={item.id} className="p-4">
                    <h4 className="text-sm font-semibold">{item.title}</h4>
                    <p className="mt-1 text-sm whitespace-pre-wrap text-muted">{item.summary}</p>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}
      </Modal>
    </section>
  )
}
