import { useState } from 'react'
import { Link } from 'react-router'

import { Alert, Button, Card, Field, FieldRow, Input, SectionHeader } from '@/components/ui'

import { type Review, useIssueCredits } from './api'
import { bufferOf } from './format'

const number = (n: number) => n.toLocaleString('en-US')

/**
 * F3 — after approval, registry staff issue the project's credits: the verified tonnes for one
 * vintage. The buffer share (from the verifier's risk rating) is kept back as insurance.
 */
export function IssueCredits({ review }: { review: Review }) {
  const issue = useIssueCredits(review.item.project_id, review.item.id)
  const [country, setCountry] = useState('Thailand')
  const [vintage, setVintage] = useState(String(new Date().getFullYear()))
  const [quantity, setQuantity] = useState('')

  if (review.issuance) {
    const { credit_id, quantity: sellable, buffer_quantity, vintage: year } = review.issuance
    return (
      <Alert className="mb-4" tone="ok" title={`${number(sellable)} credits issued for ${year}`}>
        {buffer_quantity > 0 &&
          `${number(buffer_quantity)} t are held back as insurance (the buffer pool). `}
        They are now on the public registry.
        <Link
          to={`/registry/${credit_id}`}
          className="mt-1 inline-flex min-h-11 items-center font-semibold text-accent"
        >
          View on the public registry
        </Link>
      </Alert>
    )
  }
  if (!review.can_issue) return null

  const tonnes = Number(quantity)
  const percent = review.buffer_percent ?? 0
  const buffer = tonnes > 0 ? bufferOf(tonnes, percent) : 0
  const valid = country.trim().length >= 2 && Number(vintage) > 1900 && tonnes > 0

  return (
    <div className="mb-4">
      <SectionHeader title="Issue credits" />
      <Card>
        <FieldRow>
          <Field label="Country" htmlFor="issue-country">
            <Input
              id="issue-country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            />
          </Field>
          <Field label="Vintage (year)" htmlFor="issue-vintage">
            <Input
              id="issue-vintage"
              inputMode="numeric"
              value={vintage}
              onChange={(e) => setVintage(e.target.value.replace(/\D/g, ''))}
            />
          </Field>
        </FieldRow>
        <Field
          label="Verified tonnes (tCO₂e)"
          htmlFor="issue-quantity"
          hint={
            tonnes > 0 && percent > 0
              ? `${number(buffer)} t (${percent}%) go to the buffer pool as insurance; ${number(tonnes - buffer)} t can be sold.`
              : `The verifier rated the risk, so ${percent}% is kept back as insurance.`
          }
        >
          <Input
            id="issue-quantity"
            inputMode="numeric"
            placeholder="e.g. 4800"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ''))}
          />
        </Field>
      </Card>
      {issue.isError && (
        <Alert className="mt-3" title="Credits were not issued">
          {issue.error.message}
        </Alert>
      )}
      <Button
        className="mt-3"
        disabled={!valid || issue.isPending}
        onClick={() =>
          issue.mutate({ country: country.trim(), vintage: Number(vintage), quantity: tonnes })
        }
      >
        {issue.isPending ? 'Issuing…' : 'Issue credits'}
      </Button>
    </div>
  )
}
