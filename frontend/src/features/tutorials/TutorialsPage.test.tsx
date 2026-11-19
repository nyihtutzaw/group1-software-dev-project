import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'

import { navFor } from '@/layout/nav'
import { makeUser, renderWithProviders } from '@/test/render'

import { MANUAL, TUTORIALS } from './content'
import { ManualPage } from './ManualPage'
import { TutorialPage } from './TutorialPage'
import { TutorialsPage } from './TutorialsPage'

function renderTutorial(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/system/tutorials/:id" element={<TutorialPage />} />
      <Route path="/system/tutorials" element={<p>All tutorials</p>} />
    </Routes>,
    { route, user: makeUser('admin') },
  )
}

describe('Tutorials menu', () => {
  it('is an admin-only page under System', () => {
    const item = navFor('admin').find((i) => i.id === 'tutorials')
    expect(item).toMatchObject({ path: '/system/tutorials', group: 'system' })
    for (const role of ['developer', 'verifier', 'registry_staff', 'buyer'] as const) {
      expect(navFor(role).some((i) => i.id === 'tutorials')).toBe(false)
    }
  })
})

describe('TutorialsPage', () => {
  it('lists one walkthrough per feature, F1 to F5', () => {
    renderWithProviders(<TutorialsPage />, { user: makeUser('admin') })
    const list = screen.getByRole('list', { name: 'Tutorials' })
    const links = within(list).getAllByRole('link')
    expect(links).toHaveLength(5)
    expect(TUTORIALS.map((t) => t.feature)).toEqual(['F1', 'F2', 'F3', 'F4', 'F5'])
    expect(
      within(list).getByRole('link', { name: /Project registration & evidence/ }),
    ).toHaveAttribute('href', '/system/tutorials/registration')
  })

  it('downloads the PDF user manual', () => {
    renderWithProviders(<TutorialsPage />, { user: makeUser('admin') })
    const link = screen.getByRole('link', { name: 'Download PDF' })
    expect(link).toHaveAttribute('href', MANUAL.file)
    expect(link).toHaveAttribute('download', MANUAL.downloadName)
  })
})

describe('ManualPage', () => {
  it('prints every chapter and every step, numbered', () => {
    renderWithProviders(<ManualPage />, { user: makeUser('admin') })
    expect(screen.getByRole('heading', { name: 'User Manual' })).toBeInTheDocument()
    for (const [c, t] of TUTORIALS.entries()) {
      expect(screen.getByRole('heading', { level: 2, name: t.title })).toBeInTheDocument()
      for (const [i, step] of t.steps.entries()) {
        expect(
          screen.getByRole('heading', { level: 3, name: `${c + 1}.${i + 1}${step.title}` }),
        ).toBeInTheDocument()
      }
    }
    const steps = TUTORIALS.reduce((n, t) => n + t.steps.length, 0)
    expect(screen.getAllByRole('img').length).toBeGreaterThanOrEqual(steps)
  })

  it('prints in the light theme and restores the viewer theme afterwards', () => {
    document.documentElement.dataset.theme = 'dark'
    const { unmount } = renderWithProviders(<ManualPage />, { user: makeUser('admin') })
    expect(document.documentElement.dataset.theme).toBe('light')
    unmount()
    expect(document.documentElement.dataset.theme).toBe('dark')
    delete document.documentElement.dataset.theme
  })
})

describe('TutorialPage', () => {
  it('shows the first step with its marks, legend and sample data', () => {
    renderTutorial('/system/tutorials/registration')
    expect(screen.getByRole('heading', { name: 'Project registration & evidence' })).toBeVisible()
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Start from Home' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Home page for a developer/ })).toBeInTheDocument()

    const legend = screen.getByRole('list', { name: 'On this screen' })
    const step = TUTORIALS[0].steps[0]
    expect(within(legend).getAllByRole('listitem')).toHaveLength(step.marks.length)
    expect(screen.getAllByTestId('tutorial-mark')).toHaveLength(step.marks.length)

    expect(screen.getByText('Nam Wa Hillside Reforestation')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Land title (sample)' })).toHaveAttribute(
      'href',
      '/tutorials/samples/sample-land-title.pdf',
    )
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  })

  it('moves between steps with Next, Previous and the step list', async () => {
    const user = userEvent.setup()
    renderTutorial('/system/tutorials/registration')

    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Step 2 of 6')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Step 1 · Project details' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Step 4 · Review and submit/ }))
    expect(screen.getByText('Step 5 of 6')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByText('Step 4 of 6')).toBeInTheDocument()
  })

  it('opens a step from the URL and offers the next tutorial on the last step', async () => {
    const user = userEvent.setup()
    renderTutorial('/system/tutorials/registration?step=6')
    expect(screen.getByRole('heading', { name: 'The submitted project' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Next tutorial: F2' }))
    expect(
      screen.getByRole('heading', { name: 'Geospatial boundary & overlap detection' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Step 1 of 4')).toBeInTheDocument()
  })

  it('offers the PDF manual on every walkthrough', () => {
    renderTutorial('/system/tutorials/verification')
    expect(screen.getByRole('link', { name: 'Download PDF' })).toHaveAttribute('href', MANUAL.file)
  })

  it('links to the real page only when the signed-in role can open it', () => {
    // Step 1 of F2 is on the Map page, which admins can open
    renderTutorial('/system/tutorials/boundary')
    expect(screen.getByRole('link', { name: 'Open this page' })).toHaveAttribute(
      'href',
      '/boundary',
    )
  })

  it('hides the page link for pages the role cannot open', () => {
    // Step 2 of F1 is on Submit, which only developers can open
    renderTutorial('/system/tutorials/registration?step=2')
    expect(screen.queryByRole('link', { name: 'Open this page' })).not.toBeInTheDocument()
  })

  it('says so for an unknown tutorial', () => {
    renderTutorial('/system/tutorials/nope')
    expect(screen.getByText('There is no tutorial at this address')).toBeInTheDocument()
  })

  it('keeps every mark inside its screenshot', () => {
    for (const t of TUTORIALS) {
      for (const s of t.steps) {
        for (const m of s.marks) {
          expect(m.x >= 0 && m.y >= 0 && m.x + m.w <= 100.5 && m.y + m.h <= 100.5, m.label).toBe(
            true,
          )
        }
      }
    }
  })
})
