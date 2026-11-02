import { useId, useState, type DragEvent } from 'react'

import { Alert, Card, Icon, Select, StatusChip } from '@/components/ui'
import { cn } from '@/lib/cn'

import { evidenceUrl, useUploadEvidence } from './api'
import { EVIDENCE_ACCEPT, EVIDENCE_KINDS, formatBytes } from './format'
import type { EvidenceKind, EvidenceOut } from './types'

const PICKABLE_KINDS = (Object.keys(EVIDENCE_KINDS) as EvidenceKind[]).filter(
  (k) => k !== 'additionality_proof',
)

/**
 * Evidence drop zone (mock-up `.drop`). Each file is uploaded on its own and sealed by the
 * server at once, so there is no "remove" — the text says so before anything is sent.
 * With `kind` fixed (additionality proof) there is no type picker.
 */
export function EvidenceDrop({ projectId, kind }: { projectId: number; kind?: EvidenceKind }) {
  const inputId = useId()
  const kindId = useId()
  const [picked, setPicked] = useState<EvidenceKind>('land_title')
  const [dragging, setDragging] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const upload = useUploadEvidence(projectId)

  async function send(files: FileList | null) {
    if (!files?.length) return
    const failed: string[] = []
    // One at a time: each file is its own sealed record and ledger entry
    for (const file of Array.from(files)) {
      try {
        await upload.mutateAsync({ file, kind: kind ?? picked })
      } catch (err) {
        failed.push(err instanceof Error ? err.message : `${file.name} could not be uploaded`)
      }
    }
    setErrors(failed)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    void send(e.dataTransfer.files)
  }

  return (
    <div className="grid gap-[11px]">
      {!kind && (
        <Card className="px-3.5 py-3">
          <label htmlFor={kindId} className="mb-1.5 block text-[13px] font-medium text-muted">
            Type of evidence
          </label>
          <Select
            id={kindId}
            value={picked}
            onChange={(e) => setPicked(e.target.value as EvidenceKind)}
          >
            {PICKABLE_KINDS.map((k) => (
              <option key={k} value={k}>
                {EVIDENCE_KINDS[k]}
              </option>
            ))}
          </Select>
        </Card>
      )}
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'block cursor-pointer rounded-xl border-[1.5px] border-dashed border-line-strong bg-surface-2 px-4 py-5 text-center text-[13.5px] text-muted',
          dragging && 'border-accent bg-accent-soft',
          upload.isPending && 'cursor-wait opacity-70',
        )}
      >
        <Icon name="upload" strokeWidth={2} className="mx-auto mb-1.5 size-[26px] text-accent" />
        <b className="mb-[3px] block text-[14.5px] text-ink">
          {upload.isPending
            ? 'Uploading and sealing…'
            : kind
              ? 'Add additionality proof'
              : 'Add evidence'}
        </b>
        {kind
          ? 'Financial analysis, barrier evidence or legal review (PDF, spreadsheet or photo).'
          : 'Photos, land title, survey PDF, GPS files.'}{' '}
        Files are sealed on upload — they can never be edited or replaced.
        <input
          id={inputId}
          type="file"
          multiple
          accept={EVIDENCE_ACCEPT}
          className="sr-only"
          disabled={upload.isPending}
          aria-label={kind ? 'Upload additionality proof' : 'Upload evidence'}
          onChange={(e) => {
            void send(e.target.files)
            e.target.value = ''
          }}
        />
      </label>
      {errors.length > 0 && (
        <Alert title="Some files were not accepted">
          <ul className="list-disc pl-4">
            {errors.map((msg) => (
              <li key={msg}>{msg}</li>
            ))}
          </ul>
        </Alert>
      )}
    </div>
  )
}

/** Sealed files with size and the SEALED chip (mock-up `.file`); names link to the download. */
export function EvidenceList({
  projectId,
  files,
  empty = 'No files uploaded yet.',
}: {
  projectId: number
  files: EvidenceOut[]
  empty?: string
}) {
  if (files.length === 0) {
    return <Card className="px-3.5 py-[11px] text-[13.5px] text-faint">{empty}</Card>
  }
  return (
    <Card>
      <ul aria-label="Evidence files">
        {files.map((f) => (
          <li
            key={f.id}
            className="flex items-center gap-[11px] border-b border-line px-3.5 py-[11px] text-[13.5px] last:border-b-0"
          >
            <Icon name="file" strokeWidth={2} className="size-[18px] flex-none text-faint" />
            <span className="min-w-0 flex-1">
              <a
                href={evidenceUrl(projectId, f.id)}
                className="block truncate hover:text-accent hover:underline"
                title={`${f.filename} · sha256 ${f.sha256}`}
              >
                {f.filename}
              </a>
              <span className="block text-[11.5px] text-faint">{EVIDENCE_KINDS[f.kind]}</span>
            </span>
            <span className="flex-none font-mono text-[11.5px] text-faint">
              {formatBytes(f.size_bytes)}
            </span>
            <StatusChip tone="ok">SEALED</StatusChip>
          </li>
        ))}
      </ul>
    </Card>
  )
}
