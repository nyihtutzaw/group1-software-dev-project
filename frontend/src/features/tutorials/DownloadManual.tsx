import { Icon } from '@/components/ui'

import { MANUAL } from './content'

/** Downloads the saved PDF user manual (built from these tutorials). */
export function DownloadManual() {
  return (
    <a
      href={MANUAL.file}
      download={MANUAL.downloadName}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface px-3 py-2 text-[13px] font-semibold whitespace-nowrap text-ink shadow-card transition-colors hover:bg-surface-2"
    >
      <Icon name="download" strokeWidth={2} className="size-4" />
      Download PDF
    </a>
  )
}
