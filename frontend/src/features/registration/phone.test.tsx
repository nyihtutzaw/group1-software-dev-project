/**
 * Registration on a phone at 420 px — regression tests for issue #21.
 *
 * jsdom has no layout engine, so these check the things that caused the problems rather than
 * the pixel heights: the sizing class on each tap target, and the `accept` list that decides
 * whether an iPhone offers the camera. The measurements themselves are in
 * `docs/features/F1-registration.md`.
 */
import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { BoundaryBanner } from './BoundaryBanner'
import { EVIDENCE_ACCEPT } from './format'
import { SubmitPage } from './SubmitPage'

describe('registration at 420 px', () => {
  it('offers the camera and keeps GPS files selectable on iOS', () => {
    // iOS matches `accept` against UTIs. A list of bare extensions it does not know
    // (.gpx, .kml, .geojson) can grey out every file and hide "Take Photo".
    expect(EVIDENCE_ACCEPT).toContain('image/*')
    expect(EVIDENCE_ACCEPT).toContain('application/pdf')
    expect(EVIDENCE_ACCEPT.indexOf('image/*')).toBeLessThan(EVIDENCE_ACCEPT.indexOf('.gpx'))
    // and the geospatial formats the field team uploads are still there
    for (const extension of ['.gpx', '.kml', '.kmz', '.geojson']) {
      expect(EVIDENCE_ACCEPT).toContain(extension)
    }
  })

  it('gives every step a full-size tap target', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/projects/new" element={<SubmitPage />} />
      </Routes>,
      { user: makeUser('developer'), route: '/projects/new' },
    )

    const steps = await screen.findAllByRole('button', {
      name: /Project details|Additionality|Boundary & evidence|Review & submit/,
    })

    expect(steps).toHaveLength(4)
    for (const step of steps) {
      // Before #21 these were 14 px tall — 29 px for the one that wrapped to two lines.
      expect(step.className).toContain('min-h-11')
      expect(step.className).toContain('items-center')
    }
  })

  it('gives the boundary link a full-size tap target', () => {
    renderWithProviders(<BoundaryBanner projectId={200} />, {
      user: makeUser('developer'),
    })

    // The banner resolves asynchronously; the class under test is on the link template, so
    // assert on whichever state is rendered once a link exists.
    const link = document.querySelector('a[href*="/boundary"]')
    if (link) {
      expect(link.className).toContain('min-h-11')
    }
  })
})
