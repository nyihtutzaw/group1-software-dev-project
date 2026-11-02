import { Link, useParams } from 'react-router'

import { Alert, Card, KeyValue, PageHeader, SectionHeader, StatusChip } from '@/components/ui'

import { useProject } from './api'
import { BoundaryBanner } from './BoundaryBanner'
import { EvidenceList } from './Evidence'
import { formatDate, projectChip, projectFacts, projectProgress } from './format'
import { ProgressSteps } from './ProjectRow'

/** F1 — one project: status, registration details, additionality and its sealed evidence. */
export function ProjectPage() {
  const projectId = Number(useParams().id)
  const project = useProject(Number.isInteger(projectId) ? projectId : null)

  if (project.isPending) return <PageHeader title="Project" subtitle="Loading…" />
  if (project.isError) {
    return (
      <>
        <PageHeader title="Project" />
        <Alert title="This project could not be opened">{project.error.message}</Alert>
      </>
    )
  }

  const p = project.data
  const chip = projectChip(p)
  const progress = projectProgress(p)
  const owner = p.owner_organization ? `${p.owner_name} · ${p.owner_organization}` : p.owner_name

  return (
    <>
      <PageHeader
        title={p.name}
        subtitle={
          p.submitted_at
            ? `${p.code} · submitted ${formatDate(p.submitted_at, true)} · ${owner}`
            : `${p.code} · draft · ${owner}`
        }
      />
      <div className="mb-5 flex items-center gap-3">
        <StatusChip tone={chip.tone}>{chip.label}</StatusChip>
        <ProgressSteps done={progress.done} warn={progress.warn} className="flex-1" />
      </div>

      {p.can_edit && (
        <Alert title="This project is still a draft" icon="pen">
          {p.missing.length > 0
            ? `${p.missing.length} item(s) are still needed before it can be submitted.`
            : 'Everything is in place — review and submit it.'}
          <Link to={`/projects/${p.id}/edit`} className="mt-1 block font-semibold text-accent">
            Continue registration
          </Link>
        </Alert>
      )}

      <SectionHeader title="Registration" />
      <Card>
        <KeyValue items={projectFacts(p)} />
      </Card>
      {p.baseline_summary && (
        <>
          <SectionHeader title="Baseline" />
          <Card className="p-3.5 text-[13.5px] whitespace-pre-line text-muted">
            {p.baseline_summary}
          </Card>
        </>
      )}

      <SectionHeader title="Additionality" />
      <Card className="p-3.5 text-[13.5px] whitespace-pre-line text-muted">
        {p.additionality_reasoning || 'No reasoning given yet.'}
      </Card>

      <SectionHeader
        title="Evidence"
        action={<span className="text-faint">Sealed · read-only</span>}
      />
      <EvidenceList projectId={p.id} files={p.evidence} />

      <SectionHeader title="Boundary" />
      <BoundaryBanner projectId={p.id} />
    </>
  )
}
