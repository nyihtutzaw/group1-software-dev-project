import { Link } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Card,
  EmptyState,
  PageHeader,
  SectionHeader,
  StatTile,
  StatTiles,
  StatusChip,
} from '@/components/ui'

import { useProjectList } from './api'
import { formatNumber, isDraft } from './format'
import { ProjectRow } from './ProjectRow'
import type { ProjectOut } from './types'

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/**
 * F1 — Home (mock-up "My projects"). Developers see their own projects and what needs their
 * action; registry staff and admins see every submission. Other roles get pointers to their pages.
 */
export function HomePage() {
  const { user } = useAuth()
  const role = user?.role
  const canList = role === 'developer' || role === 'registry_staff' || role === 'admin'
  const projects = useProjectList(canList)

  if (!canList) return <OtherRolesHome isVerifier={role === 'verifier'} />

  const isDeveloper = role === 'developer'
  const list = projects.data ?? []
  const registered = list.filter((p) => !isDraft(p))
  const needsAction = list.filter((p) => isDraft(p) || p.overlap)
  const awaiting = list.filter((p) => p.status === 'submitted')
  const evidence = list.reduce((sum, p) => sum + p.evidence_count, 0)

  return (
    <>
      <PageHeader
        title={isDeveloper ? 'My projects' : 'All projects'}
        subtitle={
          projects.isSuccess &&
          (isDeveloper
            ? `${registered.length} registered · ${needsAction.length} waiting on you`
            : `${plural(registered.length, 'submission')} · ${awaiting.length} awaiting verification`)
        }
      />

      {projects.isPending && <p role="status">Loading projects…</p>}
      {projects.isError && (
        <Alert title="Unable to load projects">
          {projects.error.message}{' '}
          <button
            className="font-semibold text-accent underline"
            onClick={() => projects.refetch()}
          >
            Try again
          </button>
        </Alert>
      )}

      {projects.isSuccess && (
        <>
          <StatTiles>
            <StatTile tone="accent" value={registered.length} label="Projects registered" />
            {isDeveloper ? (
              <StatTile
                tone="ok"
                value={formatNumber(verifiedTonnes(list))}
                label="tCO₂e verified"
              />
            ) : (
              <StatTile tone="ok" value={awaiting.length} label="Awaiting verification" />
            )}
            <StatTile
              tone="warn"
              value={isDeveloper ? needsAction.length : list.filter((p) => p.overlap).length}
              label={isDeveloper ? 'Needs your action' : 'Overlap flagged'}
            />
            <StatTile value={evidence} label="Evidence files" />
          </StatTiles>

          <section aria-label="Projects">
            <SectionHeader
              title={isDeveloper ? 'Active' : 'Submissions'}
              action={isDeveloper && <Link to="/projects/new">Register a project</Link>}
            />
            {list.length === 0 ? (
              <EmptyState icon="submit" title="No projects yet">
                {isDeveloper ? (
                  <Link to="/projects/new" className="font-semibold text-accent">
                    Register your first project
                  </Link>
                ) : (
                  'Projects appear here as developers register them.'
                )}
              </EmptyState>
            ) : (
              <div className="grid gap-2.5">
                {list.map((p) => (
                  <ProjectRow key={p.id} project={p} editable={isDeveloper} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <MonitoringSlot />
    </>
  )
}

/** Verified/issued projects' estimated removals — F3/F4 will replace this with verified tonnes. */
function verifiedTonnes(list: ProjectOut[]): number {
  return list
    .filter((p) => p.status === 'verified' || p.status === 'issued')
    .reduce((sum, p) => sum + (p.est_removal_tco2e ?? 0), 0)
}

/** Reserved for satellite-monitoring alerts (FR-05, deferred this term). */
function MonitoringSlot() {
  return (
    <section aria-label="Latest satellite check">
      <SectionHeader title="Latest satellite check" />
      <Card className="flex items-start justify-between gap-3 p-3.5 text-[13.5px] text-faint">
        <p>
          Satellite monitoring is not switched on yet. Canopy-loss alerts for your boundaries will
          appear here.
        </p>
        <StatusChip tone="draft">DEFERRED</StatusChip>
      </Card>
    </section>
  )
}

function OtherRolesHome({ isVerifier }: { isVerifier: boolean }) {
  return (
    <>
      <PageHeader title="Overview" subtitle="Registry activity at a glance" />
      <EmptyState icon={isVerifier ? 'verify' : 'registry'} title="Start from your workspace">
        <Link to={isVerifier ? '/verify' : '/registry'} className="font-semibold text-accent">
          {isVerifier ? 'Open the verification queue' : 'Browse the public registry'}
        </Link>
      </EmptyState>
    </>
  )
}
