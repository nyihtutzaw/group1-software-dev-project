import { describe, expect, it } from 'vitest'

import { formatDate, formatHa, formatPct, mergePolygons } from './format'
import type { Geometry } from './types'

const square: Geometry = {
  type: 'Polygon',
  coordinates: [
    [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 0],
    ],
  ],
}

describe('format', () => {
  it('formats hectares and percentages like the mock-up', () => {
    expect(formatHa(1240)).toBe('1,240.0 ha')
    expect(formatHa(38.44)).toBe('38.4 ha')
    expect(formatPct(3.1)).toBe('3.1%')
    expect(formatPct(0.5)).toBe('0.5%')
    expect(formatPct(0.04)).toBe('0.04%')
    expect(formatDate('2026-03-03T00:00:00Z')).toBe('3 Mar 2026')
  })

  it('merges drawn polygons into one geometry', () => {
    expect(mergePolygons([])).toBeNull()
    expect(mergePolygons([square])).toEqual(square)
    expect(mergePolygons([square, square])).toEqual({
      type: 'MultiPolygon',
      coordinates: [square.coordinates, square.coordinates],
    })
  })
})
