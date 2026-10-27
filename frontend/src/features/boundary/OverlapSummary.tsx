import { Alert, Card, KeyValue } from '@/components/ui'

import { formatDate, formatHa, formatPct } from './format'
import type { BoundaryCheck, OverlapFlag } from './types'

/**
 * The check result under the map: an alert (overlap or all clear) and the key figures.
 * `own` words it for the project's developer ("Your boundary…") rather than a reviewer.
 * `flags` (saved boundary only) lets a staff-resolved overlap show as cleared, not blocking.
 */
export function OverlapSummary({
  check,
  own,
  flags = [],
}: {
  check: BoundaryCheck
  own: boolean
  flags?: OverlapFlag[]
}) {
  const flagFor = (projectId: number) => flags.find((f) => f.other_project_id === projectId)
  const resolved = check.overlaps.filter(
    (o) => o.exceeds_tolerance && flagFor(o.project_id)?.status === 'resolved',
  )
  const blocking = check.overlaps.filter((o) => o.exceeds_tolerance && !resolved.includes(o))
  const disputed =
    blocking.length > 0 && blocking.every((o) => flagFor(o.project_id)?.status === 'disputed')
  const [worst] = check.overlaps
  const totalHa = check.overlaps.reduce((sum, o) => sum + o.overlap_ha, 0)
  const totalPct = check.overlaps.reduce((sum, o) => sum + o.overlap_pct, 0)

  return (
    <>
      {blocking.length > 0 ? (
        <Alert
          className="mt-[13px]"
          title={`${disputed ? 'Overlap disputed' : 'Overlap found'} — ${formatHa(blocking[0].overlap_ha)}`}
        >
          {own ? 'Your' : 'This'} boundary overlaps{' '}
          <b className="inline font-semibold text-ink">
            {blocking[0].project_code} ({blocking[0].project_name})
          </b>
          , registered {formatDate(blocking[0].registered_at)}. That is{' '}
          {formatPct(blocking[0].overlap_pct)} of {own ? 'your' : 'its'} area — above the{' '}
          {formatPct(check.tolerance_pct)} tolerance, so the submission is blocked until it is
          resolved.
          {disputed && ' The dispute is with registry staff for investigation.'}
          {blocking.length > 1 && ` It also overlaps ${blocking.length - 1} more project(s).`}
        </Alert>
      ) : resolved.length > 0 ? (
        <Alert tone="ok" className="mt-[13px]" title="Overlap resolved by registry staff">
          The {formatHa(resolved[0].overlap_ha)} ({formatPct(resolved[0].overlap_pct)}) shared with{' '}
          {resolved[0].project_code} ({resolved[0].project_name}) was investigated and cleared.
          Nothing else conflicts.
        </Alert>
      ) : worst ? (
        <Alert tone="ok" className="mt-[13px]" title="Boundary drawn — overlap within tolerance">
          Shares {formatHa(worst.overlap_ha)} ({formatPct(worst.overlap_pct)}) with{' '}
          {worst.project_code}, within the {formatPct(check.tolerance_pct)} allowed for GPS error.
          Checked against {check.checked_against.toLocaleString('en-US')} registered boundaries.
        </Alert>
      ) : (
        <Alert tone="ok" className="mt-[13px]" title="Boundary drawn — no overlap">
          Checked against {check.checked_against.toLocaleString('en-US')} registered boundaries.
          Nothing conflicts.
        </Alert>
      )}

      <Card className="mt-3">
        <KeyValue
          items={[
            { label: own ? 'Your area' : 'Area', value: formatHa(check.area_ha), mono: true },
            {
              label: 'Overlap',
              value: (
                <span className={blocking.length > 0 ? 'text-warn' : undefined}>
                  {check.overlaps.length > 0
                    ? `${formatHa(totalHa)} · ${formatPct(totalPct)}`
                    : 'None'}
                </span>
              ),
              mono: true,
            },
            { label: 'Tolerance', value: formatPct(check.tolerance_pct), mono: true },
            { label: 'Vertices', value: check.vertices, mono: true },
            {
              label: 'Checked against',
              value: `${check.checked_against.toLocaleString('en-US')} boundaries`,
              mono: true,
            },
          ]}
        />
      </Card>
    </>
  )
}
