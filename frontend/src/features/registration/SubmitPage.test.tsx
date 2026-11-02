import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { SubmitPage } from './SubmitPage'
import type { ProjectDetail } from './types'

const draft: ProjectDetail = {
  id: 200,
  code: 'CRVR-0200',
  name: 'Nan Reforestation Phase II',
  status: 'draft',
  created_at: '2026-11-02T00:00:00Z',
  updated_at: '2026-11-02T00:00:00Z',
  methodology: 'VM0047',
  crediting_start_year: 2027,
  crediting_end_year: 2047,
  area_ha: 1240,
  est_removal_tco2e: 24800,
  baseline_summary: 'Degraded grazing land.',
  additionality_reasoning: null,
  submitted_at: null,
  evidence_count: 0,
  overlap: false,
  owner_name: 'Test User',
  owner_organization: null,
  evidence: [],
  missing: ['Additionality proof upload', 'No boundary has been registered for this project.'],
  boundary_blocked: 'No boundary has been registered for this project.',
  can_edit: true,
}

type Handler = (init: RequestInit | undefined) => unknown

/** Answer fetches by "METHOD /path"; anything unexpected fails the test. */
function server(routes: Record<string, Handler | unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const key = `${init?.method ?? 'GET'} ${String(input)}`
    if (!(key in routes)) throw new Error(`Unexpected request ${key}`)
    const route = routes[key]
    const body = typeof route === 'function' ? (route as Handler)(init) : route
    return body instanceof Response ? body : Response.json(body)
  })
}

function renderAt(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/projects/new" element={<SubmitPage />} />
      <Route path="/projects/:id/edit" element={<SubmitPage />} />
      <Route path="/projects/:id" element={<p>Project page</p>} />
    </Routes>,
    { route, user: makeUser('developer') },
  )
}

describe('SubmitPage', () => {
  it('rejects invalid details with a clear message before sending anything', async () => {
    const fetch = server({})
    renderAt('/projects/new')

    await userEvent.type(screen.getByLabelText('Project name'), 'ab')
    await userEvent.type(screen.getByLabelText('Crediting start year'), '2040')
    await userEvent.type(screen.getByLabelText('Crediting end year'), '2030')
    await userEvent.type(screen.getByLabelText('Area (ha)'), 'lots')
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(screen.getByText('Enter the project name (at least 3 characters)')).toBeInTheDocument()
    expect(screen.getByText('The crediting period must end after it starts')).toBeInTheDocument()
    expect(screen.getByText('Enter the area in hectares, e.g. 1,240')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('creates the draft and moves on to additionality', async () => {
    const create = vi.fn(() => Response.json(draft, { status: 201 }))
    server({
      'POST /api/projects': create,
      'GET /api/projects/200': draft,
      'GET /api/projects': [],
    })
    renderAt('/projects/new')

    await userEvent.type(screen.getByLabelText('Project name'), 'Nan Reforestation Phase II')
    await userEvent.selectOptions(screen.getByLabelText('Methodology'), 'VM0042')
    await userEvent.type(screen.getByLabelText('Crediting start year'), '2027')
    await userEvent.type(screen.getByLabelText('Crediting end year'), '2047')
    await userEvent.type(screen.getByLabelText('Area (ha)'), '1,240')
    await userEvent.type(screen.getByLabelText('Est. removal (tCO₂e)'), '24,800')
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByText(/Step 2 of 4 · Additionality/)).toBeInTheDocument()
    expect(create).toHaveBeenCalledTimes(1)
    const [init] = create.mock.calls[0] as unknown as [RequestInit]
    expect(JSON.parse(String(init.body))).toMatchObject({
      name: 'Nan Reforestation Phase II',
      methodology: 'VM0042',
      crediting_start_year: 2027,
      crediting_end_year: 2047,
      area_ha: 1240,
      est_removal_tco2e: 24800,
      baseline_summary: null,
    })
  })

  it('saves a draft and says so', async () => {
    const save = vi.fn(() => draft)
    server({
      'GET /api/projects/200': draft,
      'PUT /api/projects/200': save,
      'GET /api/projects': [],
    })
    renderAt('/projects/200/edit')

    await userEvent.click(await screen.findByRole('button', { name: 'Save draft' }))

    expect(await screen.findByText(/Draft saved/)).toBeInTheDocument()
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('uploads additionality proof as a sealed file of that kind', async () => {
    let sent: FormData | undefined
    server({
      'GET /api/projects/200': draft,
      'GET /api/projects': [],
      'POST /api/projects/200/evidence': (init: RequestInit | undefined) => {
        sent = init?.body as FormData
        return Response.json({}, { status: 201 })
      },
    })
    renderAt('/projects/200/edit?step=2')

    const file = new File(['%PDF'], 'cost-analysis.pdf', { type: 'application/pdf' })
    await userEvent.upload(await screen.findByLabelText('Upload additionality proof'), file)

    await waitFor(() => expect(sent).toBeDefined())
    expect(sent!.get('kind')).toBe('additionality_proof')
    expect((sent!.get('file') as File).name).toBe('cost-analysis.pdf')
    expect(screen.getByText(/they can never be edited or replaced/)).toBeInTheDocument()
  })

  it('shows the server’s reason when a file is refused', async () => {
    server({
      'GET /api/projects/200': draft,
      'GET /api/projects': [],
      'GET /api/boundaries/200': Response.json({ detail: 'none' }, { status: 404 }),
      'POST /api/projects/200/evidence': Response.json(
        { detail: '“setup.exe” is not an accepted evidence format.' },
        { status: 415 },
      ),
    })
    renderAt('/projects/200/edit?step=3')

    await userEvent.upload(
      await screen.findByLabelText('Upload evidence'),
      new File(['MZ'], 'setup.exe'),
      { applyAccept: false },
    )

    expect(await screen.findByText(/is not an accepted evidence format/)).toBeInTheDocument()
    expect(await screen.findByText('No boundary yet')).toBeInTheDocument()
  })

  it('lists what is missing and only submits a complete draft', async () => {
    server({ 'GET /api/projects/200': draft, 'GET /api/projects': [] })
    renderAt('/projects/200/edit?step=4')

    expect(await screen.findByText('Additionality proof upload')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit project' })).toBeDisabled()
  })

  it('submits a complete draft and opens the project page', async () => {
    const ready = { ...draft, missing: [], boundary_blocked: null }
    const submit = vi.fn(() => ({ ...ready, status: 'submitted', can_edit: false }))
    server({
      'GET /api/projects/200': ready,
      'GET /api/projects': [],
      'POST /api/projects/200/submit': submit,
    })
    renderAt('/projects/200/edit?step=4')

    await userEvent.click(await screen.findByRole('button', { name: 'Submit project' }))

    expect(await screen.findByText('Project page')).toBeInTheDocument()
    expect(submit).toHaveBeenCalledTimes(1)
  })

  it('sends submitted projects to the read-only page', async () => {
    server({ 'GET /api/projects/200': { ...draft, status: 'submitted', can_edit: false } })
    renderAt('/projects/200/edit')

    expect(await screen.findByText('Project page')).toBeInTheDocument()
  })
})
