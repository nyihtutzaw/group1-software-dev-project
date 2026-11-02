import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Alert } from '@/components/ui'
import { useProjectBoundary } from '@/features/boundary/api'

import { formatNumber } from './format'

/** F2's overlap check, inline (mock-up "Boundary drawn — no overlap"). */
export function BoundaryBanner({ projectId }: { projectId: number }) {
  const boundary = useProjectBoundary(projectId)
  const mapLink = (label: string): ReactNode => (
    <Link to={`/boundary?project=${projectId}`} className="mt-1 block font-semibold text-accent">
      {label}
    </Link>
  )

  if (boundary.isPending) return <p role="status">Checking the boundary…</p>
  if (boundary.isError) {
    return <Alert title="The boundary could not be checked">{boundary.error.message}</Alert>
  }
  if (boundary.data === null) {
    return (
      <Alert title="No boundary yet" icon="map">
        Draw or upload the project boundary. It is checked against every registered boundary.
        {mapLink('Draw the boundary')}
      </Alert>
    )
  }
  if (boundary.data.issuance_blocked) {
    return (
      <Alert title="Boundary overlaps another project">
        {boundary.data.issuance_blocked} Submission is blocked until it is resolved.
        {mapLink('Review on the map')}
      </Alert>
    )
  }
  return (
    <Alert tone="ok" title="Boundary drawn — no overlap">
      Checked against {formatNumber(boundary.data.check.checked_against)} registered boundaries.
      Nothing conflicts.
      {mapLink('Open the map')}
    </Alert>
  )
}
