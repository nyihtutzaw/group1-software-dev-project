import { useState, type FormEvent } from 'react'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  ButtonRow,
  Card,
  Field,
  FieldRow,
  Input,
  Modal,
  SectionHeader,
  StatusChip,
  Textarea,
} from '@/components/ui'

import type { Credit } from './api'
import { date } from './format'
import { type Holding, useAllocate, useHoldings, useRetire } from './holdings-api'

/** Holdings of a batch: staff allocate ranges to buyers; a buyer retires their own credits. */
export function Holdings({ credit }: { credit: Credit }) {
  const { user } = useAuth()
  const isStaff = user?.role === 'registry_staff' || user?.role === 'admin'
  const isBuyer = user?.role === 'buyer'
  const holdings = useHoldings(credit.id, isStaff || isBuyer)
  const [retiring, setRetiring] = useState<Holding | null>(null)

  if (!isStaff && !isBuyer) return null
  const data = holdings.data
  return (
    <section aria-label={isStaff ? 'Holdings' : 'Your credits'}>
      <SectionHeader
        title={isStaff ? 'Holdings' : 'Your credits'}
        action={
          isStaff &&
          data && (
            <span className="text-xs text-faint">
              {data.allocated.toLocaleString()} allocated · {data.unallocated.toLocaleString()}{' '}
              unallocated
            </span>
          )
        }
      />
      {holdings.isPending && <p className="text-sm text-faint">Loading holdings…</p>}
      {holdings.isError && <Alert title="Could not load holdings">{holdings.error.message}</Alert>}
      {data && (
        <Card className="overflow-hidden">
          {data.items.length === 0 ? (
            <p className="px-4 py-3 text-sm text-faint">
              {isStaff
                ? 'No credits from this batch are allocated to buyers yet.'
                : 'You hold no credits from this batch.'}
            </p>
          ) : (
            <ul>
              {data.items.map((holding) => (
                <HoldingRow
                  key={holding.id}
                  holding={holding}
                  onRetire={isBuyer && credit.status === 'active' ? setRetiring : undefined}
                />
              ))}
            </ul>
          )}
        </Card>
      )}
      {isStaff && data && credit.status === 'active' && data.unallocated > 0 && (
        <AllocateForm creditId={credit.id} unallocated={data.unallocated} />
      )}
      <RetireDialog holding={retiring} onClose={() => setRetiring(null)} />
    </section>
  )
}

function HoldingRow({
  holding,
  onRetire,
}: {
  holding: Holding
  onRetire?: (holding: Holding) => void
}) {
  const retired = holding.status === 'retired'
  return (
    <li className="grid gap-2 border-b border-line px-4 py-3 text-sm last:border-b-0 desk:grid-cols-[minmax(0,1fr)_auto] desk:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <b className="font-semibold text-ink">{holding.quantity.toLocaleString()} tCO₂e</b>
          <StatusChip tone={retired ? 'draft' : 'ok'}>
            {retired ? 'Retired · locked' : 'Held'}
          </StatusChip>
          {holding.buyer_email && <span className="text-muted">{holding.buyer_email}</span>}
        </div>
        <p className="mt-0.5 font-mono text-xs break-all text-faint">{holding.serial_block}</p>
        {retired && holding.retired_at && (
          <p className="mt-0.5 text-xs text-faint">
            For {holding.beneficiary} · reporting year {holding.reporting_year} · retired{' '}
            {date(holding.retired_at)}
          </p>
        )}
      </div>
      {onRetire && !retired && (
        <Button
          className="w-auto px-3 py-2 text-xs"
          variant="ghost"
          aria-label={`Retire credits ${holding.serial_block}`}
          onClick={() => onRetire(holding)}
        >
          Retire
        </Button>
      )}
    </li>
  )
}

function AllocateForm({ creditId, unallocated }: { creditId: number; unallocated: number }) {
  const allocate = useAllocate(creditId)
  const [email, setEmail] = useState('')
  const [quantity, setQuantity] = useState('')

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    allocate.mutate(
      { buyer_email: email, quantity: Number(quantity) },
      {
        onSuccess: () => {
          setEmail('')
          setQuantity('')
        },
      },
    )
  }

  return (
    <Card className="mt-3">
      <form onSubmit={submit} aria-label="Allocate credits">
        <FieldRow>
          <Field label="Buyer email" htmlFor="allocate-email">
            <Input
              id="allocate-email"
              type="text"
              inputMode="email"
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              maxLength={255}
            />
          </Field>
          <Field label="Quantity (tCO₂e)" htmlFor="allocate-quantity">
            <Input
              id="allocate-quantity"
              type="number"
              min={1}
              max={unallocated}
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
            />
          </Field>
        </FieldRow>
        <div className="px-4 pb-4">
          <p className="mb-3 text-xs text-faint">
            The buyer needs access to this project first. The next unallocated unit range is
            assigned.
          </p>
          <Button type="submit" disabled={allocate.isPending}>
            {allocate.isPending ? 'Allocating…' : 'Allocate to buyer'}
          </Button>
        </div>
      </form>
      {allocate.isError && (
        <div className="px-4 pb-4">
          <Alert title="Could not allocate credits">{allocate.error.message}</Alert>
        </div>
      )}
    </Card>
  )
}

function RetireDialog({ holding, onClose }: { holding: Holding | null; onClose: () => void }) {
  return (
    <Modal open={holding !== null} title="Retire credits" onClose={onClose}>
      {/* Remount per holding so the form starts from that holding's defaults */}
      {holding && <RetireForm key={holding.id} holding={holding} onDone={onClose} />}
    </Modal>
  )
}

function RetireForm({ holding, onDone }: { holding: Holding; onDone: () => void }) {
  const retire = useRetire()
  const year = new Date().getFullYear()
  const [quantity, setQuantity] = useState(String(holding.quantity))
  const [beneficiary, setBeneficiary] = useState('')
  const [reason, setReason] = useState('')
  const [reportingYear, setReportingYear] = useState(String(year))

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    retire.mutate(
      {
        holdingId: holding.id,
        body: {
          quantity: Number(quantity),
          beneficiary,
          reason,
          reporting_year: Number(reportingYear),
        },
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form onSubmit={submit} aria-label="Retirement details">
      <p className="mb-3 font-mono text-xs break-all text-faint">{holding.serial_block}</p>
      <Alert title="Retirement is permanent">
        Retired credits are locked: they cannot be transferred, resold or unretired. The
        beneficiary, reason and reporting year are published in the registry.
      </Alert>
      <div className="-mx-4">
        <Field
          label="Quantity (tCO₂e)"
          htmlFor="retire-quantity"
          hint={`You hold ${holding.quantity.toLocaleString()} in this range. Retiring fewer splits it.`}
        >
          <Input
            id="retire-quantity"
            type="number"
            min={1}
            max={holding.quantity}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            required
          />
        </Field>
        <Field label="Beneficiary" htmlFor="retire-beneficiary">
          <Input
            id="retire-beneficiary"
            value={beneficiary}
            onChange={(event) => setBeneficiary(event.target.value)}
            required
            maxLength={200}
          />
        </Field>
        <Field label="Retirement reason" htmlFor="retire-reason">
          <Textarea
            id="retire-reason"
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            required
            maxLength={500}
          />
        </Field>
        <Field label="Reporting year" htmlFor="retire-year">
          <Input
            id="retire-year"
            type="number"
            min={1900}
            max={year}
            value={reportingYear}
            onChange={(event) => setReportingYear(event.target.value)}
            required
          />
        </Field>
      </div>
      {retire.isError && (
        <Alert className="mt-2" title="Could not retire credits">
          {retire.error.message}
        </Alert>
      )}
      <ButtonRow>
        <Button variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="danger" disabled={retire.isPending}>
          {retire.isPending ? 'Retiring…' : 'Retire permanently'}
        </Button>
      </ButtonRow>
    </form>
  )
}
