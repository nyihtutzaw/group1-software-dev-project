import { useState } from 'react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router'

import {
  Alert,
  Button,
  ButtonRow,
  Card,
  Field,
  FieldRow,
  Input,
  KeyValue,
  PageHeader,
  SectionHeader,
  Select,
  Textarea,
} from '@/components/ui'
import { cn } from '@/lib/cn'

import { useCreateProject, useProject, useSubmitProject, useUpdateProject } from './api'
import { BoundaryBanner } from './BoundaryBanner'
import { EvidenceDrop, EvidenceList } from './Evidence'
import { formatNumber, METHODOLOGIES, MIN_ADDITIONALITY_CHARS, projectFacts } from './format'
import { ProgressSteps } from './ProjectRow'
import type { Methodology, ProjectDetail, ProjectIn } from './types'

const STEPS = ['Project details', 'Additionality', 'Boundary & evidence', 'Review & submit']

/**
 * F1 — Register a project (mock-up "Submit"). `/projects/new` starts a draft; the draft is then
 * resumed at `/projects/:id/edit?step=N`. Every step change saves the draft first.
 */
export function SubmitPage() {
  const { id } = useParams()
  const projectId = id ? Number(id) : null
  const project = useProject(projectId)

  if (projectId !== null) {
    if (project.isPending) return <PageHeader title="Register a project" subtitle="Loading…" />
    if (project.isError) {
      return (
        <>
          <PageHeader title="Register a project" />
          <Alert title="This draft could not be opened">{project.error.message}</Alert>
        </>
      )
    }
    // Submitted (or someone else's) projects are read-only
    if (!project.data.can_edit) return <Navigate to={`/projects/${projectId}`} replace />
  }
  return <Wizard key={projectId ?? 'new'} project={project.data ?? null} />
}

// --- form state ------------------------------------------------------------------------

type Form = {
  name: string
  methodology: Methodology
  start: string
  end: string
  area: string
  removal: string
  baseline: string
  additionality: string
}
type Errors = Partial<Record<keyof Form, string>>

const text = (v: number | string | null) => (v == null ? '' : String(v))

function toForm(p: ProjectDetail | null): Form {
  return {
    name: p?.name ?? '',
    methodology: p?.methodology ?? 'VM0047',
    start: text(p?.crediting_start_year ?? null),
    end: text(p?.crediting_end_year ?? null),
    area: p?.area_ha != null ? formatNumber(p.area_ha) : '',
    removal: p?.est_removal_tco2e != null ? formatNumber(p.est_removal_tco2e) : '',
    baseline: p?.baseline_summary ?? '',
    additionality: p?.additionality_reasoning ?? '',
  }
}

/** "1,240" → 1240; "" → null; anything else → NaN */
function parseNumber(value: string): number | null {
  const clean = value.replace(/[,\s]/g, '')
  return clean === '' ? null : Number(clean)
}

function validate(form: Form): { body: ProjectIn; errors: Errors } {
  const errors: Errors = {}
  const start = parseNumber(form.start)
  const end = parseNumber(form.end)
  const area = parseNumber(form.area)
  const removal = parseNumber(form.removal)

  if (form.name.trim().length < 3) errors.name = 'Enter the project name (at least 3 characters)'
  for (const [key, year] of [
    ['start', start],
    ['end', end],
  ] as const) {
    if (year !== null && (!Number.isInteger(year) || year < 2000 || year > 2200)) {
      errors[key] = 'Enter a year such as 2027'
    }
  }
  if (!errors.start && !errors.end && start !== null && end !== null && end <= start) {
    errors.end = 'The crediting period must end after it starts'
  }
  if (area !== null && !(area > 0)) errors.area = 'Enter the area in hectares, e.g. 1,240'
  if (removal !== null && !(Number.isInteger(removal) && removal > 0)) {
    errors.removal = 'Enter whole tonnes of CO₂e, e.g. 24,800'
  }

  const blank = (v: string) => v.trim() || null
  return {
    errors,
    body: {
      name: form.name.trim(),
      methodology: form.methodology,
      crediting_start_year: start,
      crediting_end_year: end,
      area_ha: area,
      est_removal_tco2e: removal,
      baseline_summary: blank(form.baseline),
      additionality_reasoning: blank(form.additionality),
    },
  }
}

// --- wizard ----------------------------------------------------------------------------

function Wizard({ project }: { project: ProjectDetail | null }) {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const step = project ? Math.min(Math.max(Number(params.get('step')) || 1, 1), 4) : 1

  const [form, setForm] = useState(() => toForm(project))
  const [errors, setErrors] = useState<Errors>({})
  const [saved, setSaved] = useState(false)
  const create = useCreateProject()
  const update = useUpdateProject(project?.id ?? 0)
  const submit = useSubmitProject(project?.id ?? 0)
  const saving = create.isPending || update.isPending
  const saveError = create.error ?? update.error

  const set = (key: keyof Form) => (value: string) => {
    setForm((f) => ({ ...f, [key]: value }))
    setSaved(false)
  }

  /** Save the draft, then optionally move to another step. */
  async function save(next?: number) {
    const { body, errors } = validate(form)
    setErrors(errors)
    if (Object.keys(errors).length > 0) {
      if (step !== 1) setParams({ step: '1' })
      return
    }
    if (!project) {
      const created = await create.mutateAsync(body).catch(() => null)
      if (created) navigate(`/projects/${created.id}/edit?step=${next ?? 1}`, { replace: true })
      return
    }
    const ok = await update.mutateAsync(body).then(
      () => true,
      () => false,
    )
    if (!ok) return
    if (next) setParams({ step: String(next) })
    else setSaved(true)
  }

  async function onSubmit() {
    if (!project) return
    const done = await submit.mutateAsync().catch(() => null)
    if (done) navigate(`/projects/${done.id}`)
  }

  return (
    <>
      <PageHeader
        title="Register a project"
        subtitle={`Step ${step} of 4 · ${STEPS[step - 1]}${project ? ` · ${project.code}` : ''}`}
      />
      <ProgressSteps done={step} className="mb-3" />
      <StepNav step={step} enabled={!!project && !saving} onPick={(n) => void save(n)} />

      {step === 1 && <DetailsStep form={form} errors={errors} set={set} />}
      {step === 2 && project && <AdditionalityStep project={project} form={form} set={set} />}
      {step === 3 && project && <EvidenceStep project={project} />}
      {step === 4 && project && <ReviewStep project={project} />}

      {saveError && (
        <Alert className="mt-3.5" title="The draft could not be saved">
          {saveError.message}
        </Alert>
      )}
      {submit.error && (
        <Alert className="mt-3.5" title="The project could not be submitted">
          {submit.error.message}
        </Alert>
      )}
      {saved && (
        <p role="status" className="mt-3.5 text-[13.5px] text-ok">
          Draft saved — you can come back to it from Home.
        </p>
      )}

      <ButtonRow>
        {step < 4 ? (
          <>
            <Button variant="ghost" disabled={saving} onClick={() => void save()}>
              Save draft
            </Button>
            <Button disabled={saving} onClick={() => void save(step + 1)}>
              {saving ? 'Saving…' : 'Continue'}
            </Button>
          </>
        ) : (
          <>
            <Button variant="ghost" onClick={() => setParams({ step: '3' })}>
              Back
            </Button>
            <Button
              disabled={submit.isPending || (project?.missing.length ?? 1) > 0}
              onClick={() => void onSubmit()}
            >
              {submit.isPending ? 'Submitting…' : 'Submit project'}
            </Button>
          </>
        )}
      </ButtonRow>
    </>
  )
}

function StepNav({
  step,
  enabled,
  onPick,
}: {
  step: number
  enabled: boolean
  onPick: (n: number) => void
}) {
  return (
    <ol aria-label="Registration steps" className="mb-5 grid grid-cols-4 gap-1 text-[11.5px]">
      {STEPS.map((label, i) => (
        <li key={label}>
          <button
            type="button"
            disabled={!enabled || i + 1 === step}
            aria-current={i + 1 === step ? 'step' : undefined}
            onClick={() => onPick(i + 1)}
            className={cn(
              'w-full text-left leading-tight text-faint enabled:hover:text-accent disabled:cursor-default',
              i + 1 === step && 'font-semibold text-ink',
            )}
          >
            {label}
          </button>
        </li>
      ))}
    </ol>
  )
}

type StepProps = { form: Form; set: (key: keyof Form) => (value: string) => void }

function DetailsStep({ form, errors, set }: StepProps & { errors: Errors }) {
  return (
    <Card>
      <Field label="Project name" htmlFor="f-name" error={errors.name}>
        <Input
          id="f-name"
          value={form.name}
          onChange={(e) => set('name')(e.target.value)}
          placeholder="e.g. Nan Reforestation Phase II"
          maxLength={200}
        />
      </Field>
      <FieldRow>
        <Field label="Methodology" htmlFor="f-method">
          <Select
            id="f-method"
            value={form.methodology}
            onChange={(e) => set('methodology')(e.target.value)}
          >
            {Object.entries(METHODOLOGIES).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Crediting period" htmlFor="f-start" error={errors.start ?? errors.end}>
          <span className="flex items-center gap-1.5">
            <Input
              id="f-start"
              aria-label="Crediting start year"
              inputMode="numeric"
              placeholder="2027"
              className="min-w-0 flex-1 font-mono"
              value={form.start}
              onChange={(e) => set('start')(e.target.value)}
            />
            <span className="text-faint">–</span>
            <Input
              id="f-end"
              aria-label="Crediting end year"
              inputMode="numeric"
              placeholder="2047"
              className="min-w-0 flex-1 font-mono"
              value={form.end}
              onChange={(e) => set('end')(e.target.value)}
            />
          </span>
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label="Area (ha)" htmlFor="f-area" error={errors.area}>
          <Input
            id="f-area"
            inputMode="decimal"
            placeholder="1,240"
            className="font-mono"
            value={form.area}
            onChange={(e) => set('area')(e.target.value)}
          />
        </Field>
        <Field label="Est. removal (tCO₂e)" htmlFor="f-removal" error={errors.removal}>
          <Input
            id="f-removal"
            inputMode="numeric"
            placeholder="24,800"
            className="font-mono"
            value={form.removal}
            onChange={(e) => set('removal')(e.target.value)}
          />
        </Field>
      </FieldRow>
      <Field label="Baseline summary" htmlFor="f-baseline">
        <Textarea
          id="f-baseline"
          rows={3}
          maxLength={5000}
          placeholder="Land use before the project and the baseline carbon stock"
          value={form.baseline}
          onChange={(e) => set('baseline')(e.target.value)}
        />
      </Field>
    </Card>
  )
}

function AdditionalityStep({ project, form, set }: StepProps & { project: ProjectDetail }) {
  const length = form.additionality.trim().length
  const proofs = project.evidence.filter((e) => e.kind === 'additionality_proof')
  return (
    <>
      <Card>
        <Field
          label="Why is this project additional?"
          htmlFor="f-additionality"
          hint={
            length < MIN_ADDITIONALITY_CHARS
              ? `${length} / at least ${MIN_ADDITIONALITY_CHARS} characters`
              : `${length} characters`
          }
        >
          <Textarea
            id="f-additionality"
            rows={6}
            maxLength={10000}
            placeholder="Explain why the removals would not happen without carbon finance — costs, barriers, and that no law already requires it."
            value={form.additionality}
            onChange={(e) => set('additionality')(e.target.value)}
          />
        </Field>
      </Card>
      <SectionHeader title="Proof" />
      <EvidenceDrop projectId={project.id} kind="additionality_proof" />
      <div className="mt-[11px]">
        <EvidenceList projectId={project.id} files={proofs} empty="No proof uploaded yet." />
      </div>
    </>
  )
}

function EvidenceStep({ project }: { project: ProjectDetail }) {
  const files = project.evidence.filter((e) => e.kind !== 'additionality_proof')
  return (
    <>
      <SectionHeader title="Evidence" />
      <EvidenceDrop projectId={project.id} />
      <div className="mt-[11px]">
        <EvidenceList projectId={project.id} files={files} />
      </div>
      <SectionHeader title="Boundary" />
      <BoundaryBanner projectId={project.id} />
    </>
  )
}

function ReviewStep({ project }: { project: ProjectDetail }) {
  return (
    <>
      <Card>
        <KeyValue items={projectFacts(project)} />
      </Card>
      <div className="mt-3.5">
        {project.missing.length > 0 ? (
          <Alert title="Before you can submit">
            <ul className="list-disc pl-4">
              {project.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </Alert>
        ) : (
          <Alert tone="ok" title="Ready to submit">
            Once submitted the project is sealed for independent verification and can no longer be
            changed.
          </Alert>
        )}
      </div>
    </>
  )
}
