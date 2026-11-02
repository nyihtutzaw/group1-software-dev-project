// Mirrors backend/app/features/registration/schemas.py

export type Methodology = 'VM0047' | 'VM0042' | 'ACM0003' | 'VM0033'

export type EvidenceKind =
  'land_title' | 'survey' | 'photo' | 'gps' | 'spreadsheet' | 'additionality_proof' | 'other'

// F3/F4 may add more states; unknown ones are shown as they come
export type ProjectStatus = 'draft' | 'submitted' | 'verified' | 'issued' | (string & {})

export type ProjectIn = {
  name: string
  methodology: Methodology | null
  crediting_start_year: number | null
  crediting_end_year: number | null
  area_ha: number | null
  est_removal_tco2e: number | null
  baseline_summary: string | null
  additionality_reasoning: string | null
}

export type EvidenceOut = {
  id: number
  kind: EvidenceKind
  filename: string
  content_type: string
  size_bytes: number
  sha256: string
  sealed_at: string
}

export type ProjectOut = {
  id: number
  code: string
  name: string
  status: ProjectStatus
  created_at: string
  methodology: Methodology | null
  area_ha: number | null
  est_removal_tco2e: number | null
  submitted_at: string | null
  evidence_count: number
  overlap: boolean
}

export type ProjectDetail = ProjectOut & {
  owner_name: string
  owner_organization: string | null
  crediting_start_year: number | null
  crediting_end_year: number | null
  baseline_summary: string | null
  additionality_reasoning: string | null
  updated_at: string
  evidence: EvidenceOut[]
  missing: string[]
  boundary_blocked: string | null
  can_edit: boolean
}
