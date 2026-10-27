import type { Geometry, Position } from './types'

const ha = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** 1240 → "1,240.0 ha" */
export function formatHa(value: number): string {
  return `${ha.format(value)} ha`
}

/** 3.1 → "3.1%", 0.2 → "0.20%" (small values keep two decimals so they never read as 0) */
export function formatPct(value: number): string {
  return `${value.toFixed(value < 1 ? 2 : 1)}%`
}

/** "2026-03-03T…" → "3 Mar 2026" */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** Combine drawn polygons into one geometry for the API (null when there are none). */
export function mergePolygons(geometries: Geometry[]): Geometry | null {
  const polygons: Position[][][] = geometries.flatMap((g) =>
    g.type === 'Polygon' ? [g.coordinates] : g.coordinates,
  )
  if (polygons.length === 0) return null
  if (polygons.length === 1) return { type: 'Polygon', coordinates: polygons[0] }
  return { type: 'MultiPolygon', coordinates: polygons }
}
