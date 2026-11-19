import { useState } from 'react'

import { useAuth } from '@/auth/useAuth'
import { Alert, Button, Card, EmptyState, PageHeader } from '@/components/ui'

import { useLedger, useLedgerVerify, type LedgerEntry } from './api'

const VERIFY_ROLES = ['verifier', 'registry_staff', 'buyer', 'admin']

function titleCase(value: string) {
  return value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function actionTitle(action: string) {
  const [entity, ...verb] = action.split('.')
  return verb.length ? `${titleCase(entity)} — ${titleCase(verb.join(' '))}` : titleCase(action)
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

/** Who acted. Buyers get the role only (no email), so a missing email is not always the system. */
function actorLabel(entry: LedgerEntry) {
  const role = entry.actor_role ? titleCase(entry.actor_role) : null
  if (entry.actor_email) return `${entry.actor_email} · ${role ?? 'Role not recorded'}`
  return role ?? 'System'
}

function shortHash(value: string) {
  return `sha256 ${value.slice(0, 4)}…${value.slice(-4)}`
}

export function LedgerPage() {
  const [page, setPage] = useState(1)
  const { user } = useAuth()
  const entries = useLedger(page)
  const canVerify = Boolean(user && VERIFY_ROLES.includes(user.role))
  const verification = useLedgerVerify(canVerify)
  const data = entries.data
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <>
      <PageHeader
        title="Audit ledger"
        subtitle="Every action, in order · each entry seals the one before it"
      />
      {canVerify && verification.isPending && (
        <Alert className="mt-3" title="Checking ledger integrity">
          Verifying the hash chain…
        </Alert>
      )}
      {canVerify && verification.isError && (
        <Alert className="mt-3" title="Could not check ledger integrity">
          {verification.error.message}
        </Alert>
      )}
      {canVerify &&
        verification.data &&
        (verification.data.valid ? (
          <Alert
            className="mt-3"
            tone="ok"
            title={`Chain intact${data ? ` — ${data.total} ${data.total === 1 ? 'entry' : 'entries'}` : ''}`}
          >
            The ledger hash chain is valid.
          </Alert>
        ) : (
          <Alert className="mt-3" title="Chain integrity broken">
            {verification.data.error ?? 'The ledger hash chain could not be verified.'}
          </Alert>
        ))}

      <Card className="mt-3 overflow-hidden px-3.5">
        {entries.isPending ? (
          <p className="py-4 text-sm text-faint">Loading ledger entries…</p>
        ) : entries.isError ? (
          <Alert title="Could not load ledger">
            {entries.error.message}
            <Button className="mt-3" variant="ghost" onClick={() => void entries.refetch()}>
              Try again
            </Button>
          </Alert>
        ) : data?.items.length ? (
          <ol aria-label="Ledger entries">
            {data.items.map((entry, index) => (
              <li key={entry.id} className="grid grid-cols-[12px_minmax(0,1fr)] gap-x-3">
                <span className="relative flex justify-center">
                  {index < data.items.length - 1 && (
                    <span className="absolute bottom-0 top-0 w-0.5 bg-line" />
                  )}
                  <span className="relative mt-3.5 size-3 rounded-full border-2 border-accent bg-surface" />
                </span>
                <div className="min-w-0 border-b border-line py-3 last:border-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                    <b className="text-sm font-semibold text-ink">{actionTitle(entry.action)}</b>
                    <time
                      className="text-xs text-faint"
                      dateTime={entry.created_at}
                      title={new Date(entry.created_at).toLocaleString()}
                    >
                      {formatTime(entry.created_at)}
                    </time>
                  </div>
                  <p className="mt-0.5 break-words text-[13px] text-muted">{actorLabel(entry)}</p>
                  <code className="mt-1 inline-block max-w-full break-all rounded-md bg-surface-2 px-2 py-1 font-mono text-[11px] text-faint">
                    {shortHash(entry.hash)}
                  </code>
                  {Object.keys(entry.payload).length > 0 && (
                    <details className="mt-1 text-xs text-muted">
                      <summary className="w-fit cursor-pointer font-medium">Details</summary>
                      <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-2 text-xs">
                        {JSON.stringify(entry.payload, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState icon="ledger" title="No entries yet">
            Critical actions will appear here as they are recorded.
          </EmptyState>
        )}
      </Card>

      {data && pageCount > 1 && (
        <nav
          className="mt-3 flex items-center justify-between gap-3"
          aria-label="Ledger pagination"
        >
          <Button
            className="w-auto"
            variant="ghost"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </Button>
          <span className="text-sm text-muted">
            Page {page} of {pageCount}
          </span>
          <Button
            className="w-auto"
            variant="ghost"
            disabled={page >= pageCount}
            onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
          >
            Next
          </Button>
        </nav>
      )}
      <p className="mt-3 text-center text-xs text-faint">
        Entries cannot be edited or deleted. Corrections are appended as new entries.
      </p>
    </>
  )
}
