import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Field,
  PageHeader,
  Select,
} from '@/components/ui'

import {
  useBoundaries,
  useCheckBoundary,
  useImportBoundary,
  useProjectBoundary,
  useProjects,
  useSaveBoundary,
} from './api'
import { BoundaryMap } from './BoundaryMap'
import { FlagList } from './FlagList'
import { formatHa } from './format'
import { OverlapSummary } from './OverlapSummary'
import type { BoundaryFeature, Geometry, ProjectBoundary } from './types'

type ProjectOption = { id: number; code: string; name: string }

/**
 * F2 — Boundary (mock-up "Map" screen). Pick a project, draw or upload its boundary, see the
 * overlap check live, save it, and dispute or resolve overlap flags.
 */
export function BoundaryPage() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const role = user?.role
  const listsProjects = role === 'developer' || role === 'registry_staff' || role === 'admin'

  const projects = useProjects(listsProjects)
  const boundaries = useBoundaries()

  // Verifiers can't list projects (F1 rule), so they pick from registered boundaries.
  const options: ProjectOption[] | undefined = listsProjects
    ? projects.data
    : boundaries.data?.features.map((f) => ({
        id: f.properties.project_id,
        code: f.properties.code,
        name: f.properties.name,
      }))

  // An unknown or inaccessible ?project= falls back to the first project rather than "none".
  const requested = Number(params.get('project')) || null
  const project = options?.find((o) => o.id === requested) ?? options?.[0]
  const saved = useProjectBoundary(project?.id ?? null)

  const loadError = (listsProjects ? projects.error : null) ?? boundaries.error ?? saved.error
  if (loadError) {
    return (
      <>
        <PageHeader title="Boundary" />
        <Alert title="The boundary could not be loaded">{loadError.message}</Alert>
      </>
    )
  }
  if (!options || boundaries.isPending) {
    return <PageHeader title="Boundary" subtitle="Loading…" />
  }
  if (options.length === 0 || !project) {
    return (
      <>
        <PageHeader title="Boundary" />
        <EmptyState icon="map" title="No projects to show">
          {role === 'developer'
            ? 'Register a project first; its boundary is drawn here.'
            : 'No project has a registered boundary yet.'}
        </EmptyState>
      </>
    )
  }

  return (
    <>
      {saved.isPending ? (
        <PageHeader title="Boundary" subtitle={`${project.name} · loading…`} />
      ) : (
        // Remount the editor when the project or its saved version changes.
        <BoundaryEditor
          key={`${project.id}-${saved.data?.updated_at ?? 'none'}`}
          project={project}
          saved={saved.data ?? null}
          options={options}
          onSelect={(id) => setParams({ project: String(id) })}
          context={(boundaries.data?.features ?? []).filter(
            (f) => f.properties.project_id !== project.id,
          )}
          canEdit={saved.data ? saved.data.can_edit : role === 'developer' || role === 'admin'}
          canResolve={role === 'registry_staff' || role === 'admin'}
        />
      )}
    </>
  )
}

function BoundaryEditor({
  project,
  saved,
  options,
  onSelect,
  context,
  canEdit,
  canResolve,
}: {
  project: ProjectOption
  saved: ProjectBoundary | null
  options: ProjectOption[]
  onSelect: (id: number) => void
  context: BoundaryFeature[]
  canEdit: boolean
  canResolve: boolean
}) {
  const [draft, setDraft] = useState<Geometry | null>(saved?.geometry ?? null)
  const [source, setSource] = useState<'drawn' | 'uploaded'>(saved?.source ?? 'drawn')
  const [dirty, setDirty] = useState(false)
  const [drawSignal, setDrawSignal] = useState(0)
  const fileInput = useRef<HTMLInputElement>(null)

  const check = useCheckBoundary()
  const importFile = useImportBoundary()
  const save = useSaveBoundary(project.id)

  // Re-check the shape while it is being edited (debounced, nothing is saved).
  const { mutate: runCheck } = check
  useEffect(() => {
    if (!dirty || !draft) return
    const timer = setTimeout(() => runCheck({ geometry: draft, project_id: project.id }), 350)
    return () => clearTimeout(timer)
  }, [dirty, draft, project.id, runCheck])

  const current = dirty ? (draft ? check.data : undefined) : saved?.check
  const checking = dirty && !!draft && (check.isPending || check.isIdle)

  const onMapChange = (geometry: Geometry | null) => {
    setDraft(geometry)
    setSource('drawn')
    setDirty(true)
  }

  const onFile = (file: File | undefined) => {
    if (!file) return
    importFile.mutate(file, {
      onSuccess: ({ geometry }) => {
        setDraft(geometry)
        setSource('uploaded')
        setDirty(true)
      },
    })
    if (fileInput.current) fileInput.current.value = ''
  }

  const discard = () => {
    setDraft(saved?.geometry ?? null)
    setSource(saved?.source ?? 'drawn')
    setDirty(false)
    check.reset()
  }

  const subtitle = current
    ? `${project.name} · ${formatHa(current.area_ha)} · WGS 84`
    : `${project.name} · ${draft ? 'checking…' : 'no boundary yet'}`

  return (
    <>
      <PageHeader title="Boundary" subtitle={subtitle} />

      {options.length > 1 && (
        <Card className="mb-3">
          <Field label="Project" htmlFor="project">
            <Select
              id="project"
              value={project.id}
              onChange={(e) => onSelect(Number(e.target.value))}
            >
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.code} — {o.name}
                </option>
              ))}
            </Select>
          </Field>
        </Card>
      )}

      <BoundaryMap
        context={context}
        geometry={draft}
        overlaps={current?.overlaps ?? []}
        editable={canEdit}
        onChange={onMapChange}
        drawSignal={drawSignal}
        focusKey={String(project.id)}
        label={project.code}
      />

      {canEdit && (
        <p className="mt-2 text-center text-xs text-faint">
          {draft
            ? 'Drag the corners to adjust, or use the pen to draw a new shape.'
            : 'Tap the pen to draw the boundary corner by corner, or upload a GeoJSON, KML or zipped shapefile.'}
        </p>
      )}

      {importFile.isError && (
        <Alert className="mt-[13px]" title="This file could not be used">
          {importFile.error.message}
        </Alert>
      )}
      {check.isError && dirty && (
        <Alert className="mt-[13px]" title="This shape cannot be used">
          {check.error.message}
        </Alert>
      )}
      {checking && <p className="mt-3 text-center text-sm text-faint">Checking for overlaps…</p>}
      {current && !checking && (
        <OverlapSummary check={current} own={canEdit} flags={dirty ? [] : saved?.flags} />
      )}

      {save.isError && (
        <Alert className="mt-[13px]" title="Could not save the boundary">
          {save.error.message}
        </Alert>
      )}

      {canEdit && (
        <ButtonRow>
          {dirty ? (
            <>
              <Button variant="ghost" onClick={discard}>
                Discard changes
              </Button>
              <Button
                disabled={!draft || !current || save.isPending || check.isError}
                onClick={() => draft && save.mutate({ geometry: draft, source })}
              >
                {save.isPending ? 'Saving…' : 'Save boundary'}
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" onClick={() => setDrawSignal((n) => n + 1)}>
                {saved ? 'Re-draw boundary' : 'Draw boundary'}
              </Button>
              <Button
                variant="ghost"
                disabled={importFile.isPending}
                onClick={() => fileInput.current?.click()}
              >
                {importFile.isPending ? 'Reading file…' : 'Upload a file'}
              </Button>
            </>
          )}
        </ButtonRow>
      )}
      <input
        ref={fileInput}
        type="file"
        accept=".geojson,.json,.kml,.kmz,.zip"
        className="hidden"
        aria-label="Boundary file"
        onChange={(e) => onFile(e.target.files?.[0])}
      />

      {saved && !dirty && (
        <FlagList
          projectId={project.id}
          flags={saved.flags}
          issuanceBlocked={saved.issuance_blocked}
          canDispute={saved.can_edit}
          canResolve={canResolve}
        />
      )}
    </>
  )
}
