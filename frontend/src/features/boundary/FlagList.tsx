import { useState } from 'react'

import {
  Alert,
  Button,
  ButtonRow,
  Card,
  Field,
  SectionHeader,
  StatusChip,
  Textarea,
  type ChipTone,
} from '@/components/ui'

import { useDisputeFlag, useResolveFlag } from './api'
import { formatDate, formatHa, formatPct } from './format'
import type { FlagStatus, OverlapFlag } from './types'

const TONE: Record<FlagStatus, ChipTone> = {
  open: 'warn',
  disputed: 'wait',
  resolved: 'ok',
  superseded: 'draft',
}

type Action = { kind: 'dispute' | 'resolve'; flagId: number } | null

/**
 * Saved overlap flags for a project. The developer can dispute an open flag;
 * registry staff resolve open or disputed ones (FR-04 investigation step).
 */
export function FlagList({
  projectId,
  flags,
  issuanceBlocked,
  canDispute,
  canResolve,
}: {
  projectId: number
  flags: OverlapFlag[]
  issuanceBlocked: string | null
  canDispute: boolean
  canResolve: boolean
}) {
  const [action, setAction] = useState<Action>(null)
  const [text, setText] = useState('')
  const dispute = useDisputeFlag(projectId)
  const resolve = useResolveFlag(projectId)
  const mutation = action?.kind === 'resolve' ? resolve : dispute

  if (flags.length === 0) return null

  const submit = () => {
    if (!action) return
    mutation.mutate(
      { flagId: action.flagId, text },
      {
        onSuccess: () => {
          setAction(null)
          setText('')
        },
      },
    )
  }

  return (
    <section className="mt-7">
      <SectionHeader title="Overlap flags" />
      <Card>
        {flags.map((flag) => (
          <div key={flag.id} className="border-b border-line px-3.5 py-3 last:border-b-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <b className="block text-sm font-semibold">
                  {flag.other_project_code} · {flag.other_project_name}
                </b>
                <span className="block font-mono text-xs text-faint">
                  {formatHa(flag.overlap_ha)} · {formatPct(flag.overlap_pct)} · flagged{' '}
                  {formatDate(flag.created_at)}
                </span>
              </div>
              <StatusChip tone={TONE[flag.status]}>{flag.status.toUpperCase()}</StatusChip>
            </div>
            {flag.dispute_reason && (
              <p className="mt-2 text-[13px] text-muted">
                <b className="font-semibold text-ink">Dispute:</b> {flag.dispute_reason}
              </p>
            )}
            {flag.resolution_note && (
              <p className="mt-2 text-[13px] text-muted">
                <b className="font-semibold text-ink">Resolution:</b> {flag.resolution_note}
              </p>
            )}
            {action === null && (
              <div className="mt-2.5 flex gap-2">
                {canDispute && flag.status === 'open' && (
                  <button
                    type="button"
                    className="text-[13px] font-semibold text-warn"
                    onClick={() => setAction({ kind: 'dispute', flagId: flag.id })}
                  >
                    Dispute overlap
                  </button>
                )}
                {canResolve && (flag.status === 'open' || flag.status === 'disputed') && (
                  <button
                    type="button"
                    className="text-[13px] font-semibold text-accent"
                    onClick={() => setAction({ kind: 'resolve', flagId: flag.id })}
                  >
                    Resolve overlap
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </Card>

      {action && (
        <div className="mt-3">
          <Card>
            <Field
              label={action.kind === 'dispute' ? 'Why is the overlap wrong?' : 'Resolution note'}
              htmlFor="flag-text"
              hint={
                action.kind === 'dispute'
                  ? 'Registry staff will investigate. Recorded in the audit ledger.'
                  : 'Clears the flag and unblocks issuance. Recorded in the audit ledger.'
              }
            >
              <Textarea
                id="flag-text"
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </Field>
          </Card>
          {mutation.isError && (
            <Alert className="mt-3" title="Could not save">
              {mutation.error.message}
            </Alert>
          )}
          <ButtonRow>
            <Button variant="ghost" onClick={() => setAction(null)}>
              Cancel
            </Button>
            <Button
              variant={action.kind === 'dispute' ? 'danger' : 'primary'}
              disabled={
                mutation.isPending || text.trim().length < (action.kind === 'dispute' ? 10 : 5)
              }
              onClick={submit}
            >
              {action.kind === 'dispute' ? 'Send dispute' : 'Resolve'}
            </Button>
          </ButtonRow>
        </div>
      )}

      {issuanceBlocked && (
        <p className="mt-2.5 text-center text-xs text-faint">
          Credit issuance is blocked: {issuanceBlocked}
        </p>
      )}
    </section>
  )
}
