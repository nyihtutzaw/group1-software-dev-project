import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { makeUser, renderWithProviders } from '@/test/render'

import { AssistantPage } from './AssistantPage'
import { Markdown } from './Markdown'

const STATUS = {
  enabled: true,
  model: 'test/model',
  documents: ['README.md', 'docs/features/F2-boundary.md'],
}
const STORAGE_KEY = 'crvr.assistant.1' // makeUser() has id 1

/** Status from GET /admin/assistant; `answer` (or an error) from POST …/chat. */
function mockApi(answer: Response | (() => Response), status = STATUS) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/admin/assistant') return Response.json(status)
    return typeof answer === 'function' ? answer() : answer
  })
}

function renderPage() {
  return renderWithProviders(<AssistantPage />, { user: makeUser('admin') })
}

beforeEach(() => sessionStorage.clear())
afterEach(() => vi.restoreAllMocks())

describe('AssistantPage', () => {
  it('survives leaving the page when scrollIntoView returns a Promise (Chrome)', async () => {
    // Chrome's scrollIntoView returns a Promise. An effect that returned it handed React a
    // non-function cleanup, so leaving the page crashed the app ("l is not a function").
    Element.prototype.scrollIntoView = vi.fn(() => Promise.resolve()) as never
    mockApi(new Response('ok'))
    const { unmount } = renderPage()
    await screen.findByLabelText('Your question')

    expect(() => unmount()).not.toThrow()
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
  })

  it('asks a question, shows the streamed answer and keeps the chat in this tab', async () => {
    const fetch = mockApi(new Response('Overlaps above **0.5%** block submission.'))
    renderPage()

    const box = await screen.findByLabelText('Your question')
    await waitFor(() => expect(box).toBeEnabled())
    await userEvent.type(box, 'When does an overlap block?{Enter}')

    expect(await screen.findByText('0.5%')).toHaveProperty('tagName', 'STRONG')
    expect(screen.getByText('When does an overlap block?')).toBeInTheDocument()

    const [, init] = fetch.mock.calls.find(([url]) => String(url).endsWith('/chat'))!
    expect(JSON.parse(String(init?.body))).toEqual({
      messages: [{ role: 'user', content: 'When does an overlap block?' }],
    })
    await waitFor(() =>
      expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY)!)).toEqual([
        { role: 'user', content: 'When does an overlap block?' },
        { role: 'assistant', content: 'Overlaps above **0.5%** block submission.' },
      ]),
    )
  })

  it('restores the chat from this tab and clears it', async () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { role: 'user', content: 'Who owns F2?' },
        { role: 'assistant', content: 'Nyi Htut Zaw owns F2.' },
      ]),
    )
    mockApi(new Response(''))
    renderPage()

    expect(screen.getByText('Nyi Htut Zaw owns F2.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear chat' }))

    expect(screen.queryByText('Nyi Htut Zaw owns F2.')).not.toBeInTheDocument()
    expect(screen.getByText('Ask anything about CRVR')).toBeInTheDocument()
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('sends the earlier messages with a follow-up question', async () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { role: 'user', content: 'Who owns F2?' },
        { role: 'assistant', content: 'Nyi Htut Zaw.' },
      ]),
    )
    const fetch = mockApi(() => new Response('PostGIS.'))
    renderPage()

    const box = await screen.findByLabelText('Your question')
    await waitFor(() => expect(box).toBeEnabled())
    await userEvent.type(box, 'What does it use?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('PostGIS.')).toBeInTheDocument()
    const [, init] = fetch.mock.calls.find(([url]) => String(url).endsWith('/chat'))!
    expect(JSON.parse(String(init?.body)).messages).toHaveLength(3)
  })

  it('puts the question back and explains when there is no answer', async () => {
    mockApi(Response.json({ detail: 'Too many questions in a minute.' }, { status: 429 }))
    renderPage()

    const box = await screen.findByLabelText('Your question')
    await waitFor(() => expect(box).toBeEnabled())
    await userEvent.type(box, 'Hello?{Enter}')

    expect(await screen.findByText('Too many questions in a minute.')).toBeInTheDocument()
    expect(box).toHaveValue('Hello?')
    expect(screen.getByText('Ask anything about CRVR')).toBeInTheDocument()
  })

  it('says when the server has no API key', async () => {
    mockApi(new Response(''), { ...STATUS, enabled: false })
    renderPage()

    expect(await screen.findByText('The assistant is not set up on this server')).toBeVisible()
    expect(screen.getByLabelText('Your question')).toBeDisabled()
  })
})

describe('Markdown', () => {
  it('renders lists, code and links without injecting HTML', () => {
    render(
      <Markdown>
        {[
          'Steps:',
          '',
          '- Run `sh scripts/start.sh`',
          '- See [the docs](https://example.com/docs)',
          '',
          '<img src=x onerror=alert(1)>',
        ].join('\n')}
      </Markdown>,
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('sh scripts/start.sh').tagName).toBe('CODE')
    expect(screen.getByRole('link', { name: 'the docs' })).toHaveAttribute(
      'href',
      'https://example.com/docs',
    )
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })

  it('renders a pipe table', () => {
    render(
      <Markdown>
        {['| Methodology | Tolerance |', '|---|:---:|', '| VM0047 | **0.5%** |'].join('\n')}
      </Markdown>,
    )
    expect(screen.getByRole('columnheader', { name: 'Methodology' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('cell', { name: '0.5%' })).toBeInTheDocument()
  })
})
