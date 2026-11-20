import type { ReactNode } from 'react'

/*
 * A small, safe Markdown renderer for the assistant's answers: paragraphs, headings, bullet and
 * numbered lists, fenced code, and inline `code`, **bold**, _italic_ and http(s) links. Everything
 * becomes React elements (no HTML injection). Simple pipe tables become tables.
 */

type Block =
  | { kind: 'p' | 'h'; text: string }
  | { kind: 'ul' | 'ol'; items: string[] }
  | { kind: 'pre'; text: string }
  | { kind: 'table'; rows: string[][] }

const BULLET = /^\s*[-*+]\s+/
const NUMBERED = /^\s*\d+[.)]\s+/
const HEADING = /^#{1,6}\s+/
const TABLE_RULE = /^\|?[\s:|-]+\|?$/ // |---|:---:|

function cells(row: string): string[] {
  return row
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function parse(markdown: string): Block[] {
  const blocks: Block[] = []
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n')
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (line.trim().startsWith('```')) {
      const code: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) code.push(lines[i++])
      i++ // closing fence (or end of a still-streaming answer)
      blocks.push({ kind: 'pre', text: code.join('\n') })
    } else if (!line.trim()) {
      i++
    } else if (HEADING.test(line)) {
      blocks.push({ kind: 'h', text: line.replace(HEADING, '') })
      i++
    } else if (line.trim().startsWith('|')) {
      const rows: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(lines[i++].trim())
      blocks.push({ kind: 'table', rows: rows.filter((r) => !TABLE_RULE.test(r)).map(cells) })
    } else if (BULLET.test(line) || NUMBERED.test(line)) {
      const marker = BULLET.test(line) ? BULLET : NUMBERED
      const items: string[] = []
      while (i < lines.length && lines[i].trim()) {
        if (marker.test(lines[i])) items.push(lines[i].replace(marker, ''))
        else if (BULLET.test(lines[i]) || NUMBERED.test(lines[i])) items.push(lines[i].trim())
        else if (items.length) items[items.length - 1] += ` ${lines[i].trim()}`
        i++
      }
      blocks.push({ kind: marker === BULLET ? 'ul' : 'ol', items })
    } else {
      const text: string[] = []
      while (
        i < lines.length &&
        lines[i].trim() &&
        !HEADING.test(lines[i]) &&
        !BULLET.test(lines[i]) &&
        !NUMBERED.test(lines[i]) &&
        !lines[i].trim().startsWith('```')
      ) {
        text.push(lines[i++].replace(/^>\s?/, '').trim())
      }
      blocks.push({ kind: 'p', text: text.join(' ') })
    }
  }
  return blocks
}

const INLINE =
  /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])|(?<!\w)_([^_]+)_(?!\w)/g

function inline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  for (const m of text.matchAll(INLINE)) {
    const key = m.index ?? 0
    if (key > last) out.push(text.slice(last, key))
    if (m[1] !== undefined)
      out.push(
        <code key={key} className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.85em]">
          {m[1]}
        </code>,
      )
    else if (m[2] !== undefined)
      out.push(
        <strong key={key} className="font-semibold">
          {inline(m[2])}
        </strong>,
      )
    else if (m[3] !== undefined)
      out.push(
        <a
          key={key}
          href={m[4]}
          target="_blank"
          rel="noreferrer"
          className="text-accent underline hover:text-accent-ink"
        >
          {m[3]}
        </a>,
      )
    else out.push(<em key={key}>{m[5] ?? m[6]}</em>)
    last = key + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="grid gap-2.5 text-sm leading-relaxed text-ink">
      {parse(children).map((block, i) => {
        switch (block.kind) {
          case 'h':
            return (
              <p key={i} className="font-semibold">
                {inline(block.text)}
              </p>
            )
          case 'p':
            return <p key={i}>{inline(block.text)}</p>
          case 'pre':
            return (
              <pre
                key={i}
                className="overflow-x-auto rounded-lg border border-line bg-surface-2 p-3 font-mono text-xs leading-normal"
              >
                <code>{block.text}</code>
              </pre>
            )
          case 'table': {
            const [head = [], ...body] = block.rows
            return (
              <div key={i} className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full border-collapse text-left text-[13px]">
                  <thead className="bg-surface-2">
                    <tr>
                      {head.map((cell, j) => (
                        <th key={j} className="px-3 py-2 font-semibold">
                          {inline(cell)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {body.map((row, r) => (
                      <tr key={r} className="border-t border-line">
                        {row.map((cell, j) => (
                          <td key={j} className="px-3 py-2 align-top">
                            {inline(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          case 'ul':
          case 'ol': {
            const List = block.kind
            return (
              <List
                key={i}
                className={`grid gap-1 pl-5 ${block.kind === 'ul' ? 'list-disc' : 'list-decimal'}`}
              >
                {block.items.map((item, j) => (
                  <li key={j}>{inline(item)}</li>
                ))}
              </List>
            )
          }
        }
      })}
    </div>
  )
}
