// Mirrors backend/app/features/boundary/schemas.py

export type Position = number[] // [longitude, latitude]

export type Geometry =
  | { type: 'Polygon'; coordinates: Position[][] }
  | { type: 'MultiPolygon'; coordinates: Position[][][] }

export type Overlap = {
  project_id: number
  project_code: string
  project_name: string
  registered_at: string
  overlap_m2: number
  overlap_ha: number
  overlap_pct: number // % of the checked boundary's area
  other_overlap_pct: number // % of the other project's area
  // Limits for this pair: the stricter of the two projects' methodology rules
  tolerance_pct: number
  cap_ha: number
  exceeds_tolerance: boolean // blocks: above the tolerance or the area cap
  reason: OverlapReason | null
  intersection: Geometry
}

/** Why an overlap blocks (the first rule it breaks). */
export type OverlapReason =
  'share_of_this' | 'share_of_other' | 'area_cap' | 'combined_share' | 'combined_area'

export type BoundaryCheck = {
  area_m2: number
  area_ha: number
  vertices: number
  checked_against: number
  methodology: string | null // of the checked project; picks the rule
  tolerance_pct: number // the checked project's own rule
  cap_ha: number
  overlaps: Overlap[]
  blocked: boolean
}

export type FlagStatus = 'open' | 'disputed' | 'resolved' | 'superseded'

export type OverlapFlag = {
  id: number
  other_project_id: number
  other_project_code: string
  other_project_name: string
  overlap_ha: number
  overlap_pct: number
  status: FlagStatus
  dispute_reason: string | null
  resolution_note: string | null
  created_at: string
  resolved_at: string | null
}

export type ProjectBoundary = {
  project_id: number
  project_code: string
  project_name: string
  geometry: Geometry
  source: 'drawn' | 'uploaded'
  updated_at: string
  check: BoundaryCheck
  flags: OverlapFlag[]
  issuance_blocked: string | null
  can_edit: boolean
}

export type BoundaryFeature = {
  type: 'Feature'
  geometry: Geometry
  properties: { project_id: number; code: string; name: string; area_ha: number; flagged: boolean }
}

export type BoundaryCollection = { type: 'FeatureCollection'; features: BoundaryFeature[] }

// From F1's GET /api/projects
export type ProjectSummary = { id: number; code: string; name: string; status: string }
