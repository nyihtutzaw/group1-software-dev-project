import type { ChipTone, KeyValueItem } from '@/components/ui'

import type { EvidenceKind, Methodology, ProjectDetail, ProjectOut } from './types'

export const METHODOLOGIES: Record<Methodology, string> = {
  VM0047: 'VM0047 Reforestation',
  VM0042: 'VM0042 Agriculture',
  ACM0003: 'ACM0003 Soil carbon',
  VM0033: 'VM0033 Tidal wetland',
}

export const EVIDENCE_KINDS: Record<EvidenceKind, string> = {
  land_title: 'Land title',
  survey: 'Survey',
  photo: 'Photos',
  gps: 'GPS / map file',
  spreadsheet: 'Spreadsheet',
  additionality_proof: 'Additionality proof',
  other: 'Other',
}

// Same list as the backend (service.EVIDENCE_EXTENSIONS) — the server has the final say
export const EVIDENCE_ACCEPT =
  '.pdf,.jpg,.jpeg,.png,.heic,.webp,.tif,.tiff,.xlsx,.xls,.ods,.csv,.gpx,.kml,.kmz,.geojson,.zip'

export const MIN_ADDITIONALITY_CHARS = 50

/** Status chip for a project row. An unresolved overlap outranks the workflow status. */
export function projectChip(project: Pick<ProjectOut, 'status' | 'overlap'>): {
  tone: ChipTone
  label: string
} {
  if (project.overlap) return { tone: 'warn', label: 'OVERLAP' }
  switch (project.status) {
    case 'draft':
      return { tone: 'draft', label: 'DRAFT' }
    case 'submitted':
      return { tone: 'wait', label: 'SUBMITTED' }
    case 'verified':
      return { tone: 'ok', label: 'VERIFIED' }
    case 'issued':
      return { tone: 'accent', label: 'ISSUED' }
    default:
      return { tone: 'wait', label: project.status.toUpperCase().replaceAll('_', ' ') }
  }
}

/** How far along the 4-step journey (registered → submitted → verified → issued) a project is. */
export function projectProgress(project: Pick<ProjectOut, 'status' | 'overlap'>): {
  done: number
  warn: boolean
} {
  const steps: Record<string, number> = { draft: 1, submitted: 2, verified: 3, issued: 4 }
  const done = steps[project.status] ?? 2
  return { done, warn: project.overlap }
}

export const isDraft = (p: Pick<ProjectOut, 'status'>) => p.status === 'draft'

const number = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 })
export const formatNumber = (n: number) => number.format(n)

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Fixed names: newer ICU spells en-GB September "Sept", the mock-up uses "Sep"
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "12 Sep", or "12 Sep 2026" with the year. */
export function formatDate(iso: string, withYear = false): string {
  const d = new Date(iso)
  const day = String(d.getDate()).padStart(2, '0')
  return `${day} ${MONTHS[d.getMonth()]}${withYear ? ` ${d.getFullYear()}` : ''}`
}

/** "1,240 ha · VM0047 · submitted 12 Sep" — the grey line on a project row. */
export function projectMeta(project: ProjectOut): string {
  const parts = [
    project.area_ha != null ? `${formatNumber(project.area_ha)} ha` : '—',
    project.methodology ?? '—',
  ]
  if (project.status === 'draft') parts.push('draft, not submitted')
  else if (project.submitted_at) parts.push(`submitted ${formatDate(project.submitted_at)}`)
  return parts.join(' · ')
}

/** Key facts shown on the review step and the project page. */
export function projectFacts(p: ProjectDetail): KeyValueItem[] {
  const dash = '—'
  return [
    { label: 'Project ID', value: p.code, mono: true },
    { label: 'Name', value: p.name },
    { label: 'Methodology', value: p.methodology ? METHODOLOGIES[p.methodology] : dash },
    {
      label: 'Crediting period',
      value:
        p.crediting_start_year && p.crediting_end_year
          ? `${p.crediting_start_year} – ${p.crediting_end_year}`
          : dash,
      mono: true,
    },
    {
      label: 'Area',
      value: p.area_ha != null ? `${formatNumber(p.area_ha)} ha` : dash,
      mono: true,
    },
    {
      label: 'Est. removal',
      value: p.est_removal_tco2e != null ? `${formatNumber(p.est_removal_tco2e)} tCO₂e` : dash,
      mono: true,
    },
    { label: 'Evidence files', value: String(p.evidence.length), mono: true },
  ]
}
