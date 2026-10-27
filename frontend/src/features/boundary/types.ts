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
  overlap_pct: number
  exceeds_tolerance: boolean
  intersection: Geometry
}

export type BoundaryCheck = {
  area_m2: number
  area_ha: number
  vertices: number
  checked_against: number
  tolerance_pct: number
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
