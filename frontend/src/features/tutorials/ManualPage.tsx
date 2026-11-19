import { useEffect } from 'react'
import { Link } from 'react-router'

import { ROLE_LABELS } from '@/auth/types'
import { Icon, StatusChip } from '@/components/ui'
import { Brand } from '@/layout/Brand'

import { AnnotatedScreenshot, MarkNumber } from './AnnotatedScreenshot'
import { MANUAL, ROLE_GUIDE, TUTORIALS } from './content'
import type { Tutorial, TutorialStep } from './types'

// One step per A4 page: the screenshot is as large as fits beside its text and legend.
const MAX_IMAGE_HEIGHT_MM = 178

// A4 with room for the page-number footer. Used by Print → Save as PDF and by the PDF script.
const PAGE_CSS = '@page { size: A4; margin: 14mm 14mm 16mm; }'

const sectionTitle = 'text-[20px] font-semibold tracking-[-0.02em] text-ink'

/** The printed manual is always light, whatever theme the viewer picked. */
function useLightTheme() {
  useEffect(() => {
    const root = document.documentElement
    const previous = root.dataset.theme
    root.dataset.theme = 'light'
    return () => {
      if (previous) root.dataset.theme = previous
      else delete root.dataset.theme
    }
  }, [])
}

function Cover() {
  const preview = TUTORIALS[0].steps[0]
  return (
    <section className="flex min-h-[260mm] flex-col">
      <Brand />
      <div className="mt-[30mm]">
        <p className="text-sm font-semibold text-accent">Carbon Removal Verification Registry</p>
        <h1 className="mt-2 text-[40px] leading-[1.1] font-semibold tracking-[-0.03em] text-ink">
          User Manual
        </h1>
        <p className="mt-3 max-w-[140mm] text-base text-muted">
          A step-by-step guide to every feature, from registering a carbon-removal project to
          retiring the credits it earns, with annotated screenshots of the real application.
        </p>
      </div>
      <div className="mt-[14mm] overflow-hidden rounded-xl border border-line shadow-lg">
        <img
          src={preview.image}
          alt=""
          className="block aspect-[16/8] w-full object-cover object-top"
        />
      </div>
      <dl className="mt-auto grid grid-cols-4 gap-4 border-t border-line pt-5 text-[13px]">
        {[
          ['Version', MANUAL.version],
          ['Date', MANUAL.date],
          ['Audience', 'All five roles'],
          ['Chapters', `${TUTORIALS.length} features`],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-faint">{label}</dt>
            <dd className="mt-0.5 font-semibold text-ink">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Introduction() {
  const steps = TUTORIALS.reduce((n, t) => n + t.steps.length, 0)
  return (
    <section className="break-before-page">
      <h2 className={sectionTitle}>How to use this manual</h2>
      <div className="mt-3 grid gap-3 text-sm text-muted">
        <p>
          CRVR is a registry where project developers register carbon-removal projects and their
          land boundaries, independent verifiers review them, registry staff approve them and issue
          credits, and buyers trace every credit back to its evidence. Every critical action is
          sealed in a tamper-evident audit ledger.
        </p>
        <p>
          The manual has one chapter per feature ({TUTORIALS.length} chapters, {steps} steps). Each
          step names the role that performs it, explains what to do, and shows a screenshot of the
          real screen. Numbered marks on the screenshot match the numbered list below it:
        </p>
        <div className="flex items-center gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3">
          <span className="relative inline-block h-8 w-28 rounded-md border-2 border-purple">
            <MarkNumber n={1} className="absolute -top-2.5 -right-2.5 size-5 text-[11px]" />
          </span>
          <span className="text-[13px]">
            A purple box marks the part of the screen the step is about; its number points to the
            explanation in the list.
          </span>
        </div>
        <p>
          All chapters follow one fictional sample project,{' '}
          <b className="text-ink">Nam Wa Hillside Reforestation</b>, from registration to a retired
          credit, and list the values and files used, so you can repeat every step. The same
          walkthroughs are in the application under <b className="text-ink">System › Tutorials</b>{' '}
          (registry admins), where the sample files can be downloaded.
        </p>
      </div>

      <h3 className="mt-8 mb-3 text-[15px] font-semibold text-ink">Roles</h3>
      <table className="w-full border-collapse text-[13px]">
        <tbody>
          {ROLE_GUIDE.map(({ role, duties }) => (
            <tr key={role} className="border-t border-line last:border-b">
              <th scope="row" className="w-44 py-2 pr-4 text-left align-top font-semibold text-ink">
                {ROLE_LABELS[role]}
              </th>
              <td className="py-2 text-muted">{duties}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-faint">
        What each role sees depends on the account you sign in with; menus hide pages your role
        cannot open, and the server enforces the same rules.
      </p>
    </section>
  )
}

function Contents() {
  return (
    <section className="break-before-page">
      <h2 className={sectionTitle}>Contents</h2>
      <ol className="mt-5 grid gap-5">
        {TUTORIALS.map((t, c) => (
          <li key={t.id} className="break-inside-avoid">
            <p className="flex items-center gap-2 text-[15px] font-semibold text-ink">
              <span className="font-mono text-[13px] text-accent">{c + 1}</span>
              {t.title}
              <span className="text-xs font-normal text-faint">{t.feature}</span>
            </p>
            <ol className="mt-1.5 grid gap-1 border-l border-line pl-4 text-[13px] text-muted">
              {t.steps.map((s, i) => (
                <li key={s.title} className="flex gap-3">
                  <span className="w-8 font-mono text-[12px] text-faint">
                    {c + 1}.{i + 1}
                  </span>
                  <span className="flex-1">{s.title}</span>
                  <span className="text-xs text-faint">{ROLE_LABELS[s.role]}</span>
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </section>
  )
}

function Step({ step, number }: { step: TutorialStep; number: string }) {
  const [width, height] = step.size
  return (
    <article className="break-before-page">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 className="text-[15px] font-semibold text-ink">
          <span className="mr-1.5 font-mono text-[13px] text-accent">{number}</span>
          {step.title}
        </h3>
        <StatusChip tone="draft">{ROLE_LABELS[step.role]}</StatusChip>
      </div>
      <p className="mt-1.5 mb-3 text-[13px] text-muted">{step.body}</p>
      <div
        className="mx-auto"
        style={{ maxWidth: `min(100%, ${((MAX_IMAGE_HEIGHT_MM * width) / height).toFixed(1)}mm)` }}
      >
        <AnnotatedScreenshot step={step} link={false} />
      </div>
      <ol className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px] text-muted">
        {step.marks.map((mark, i) => (
          <li key={mark.label} className="flex items-start gap-2">
            <MarkNumber n={i + 1} className="size-5 text-[11px]" />
            <span className="pt-px">{mark.label}</span>
          </li>
        ))}
      </ol>
      {step.tip && (
        <p className="mt-3 rounded-lg border border-line bg-surface-2 px-3 py-2 text-[12.5px] text-muted">
          <b className="font-semibold text-ink">Tip · </b>
          {step.tip}
        </p>
      )}
    </article>
  )
}

function Chapter({ tutorial, number }: { tutorial: Tutorial; number: number }) {
  return (
    <section className="break-before-page">
      <div className="flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-lg bg-accent-soft text-accent">
          <Icon name={tutorial.icon} className="size-5" />
        </span>
        <StatusChip tone="accent">{tutorial.feature}</StatusChip>
        <span className="text-xs text-faint">Chapter {number}</span>
      </div>
      <h2 className={`mt-3 ${sectionTitle}`}>{tutorial.title}</h2>
      <p className="mt-1.5 text-sm text-muted">{tutorial.summary}</p>
      <p className="mt-1.5 text-xs text-faint">
        For: {tutorial.roles.map((r) => ROLE_LABELS[r]).join(', ')}
      </p>

      <div className="mt-5 grid grid-cols-[minmax(0,1fr)_auto] gap-6 rounded-xl border border-line p-4 break-inside-avoid">
        <div>
          <h3 className="mb-2 text-[13px] font-semibold text-ink">Sample data</h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[12.5px]">
            {tutorial.sample.map((s) => (
              <div key={s.label} className="contents">
                <dt className="text-faint">{s.label}</dt>
                <dd className="text-ink">{s.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        {tutorial.files.length > 0 && (
          <div className="max-w-[62mm]">
            <h3 className="mb-2 text-[13px] font-semibold text-ink">Sample files</h3>
            <ul className="grid gap-2 text-[12.5px]">
              {tutorial.files.map((f) => (
                <li key={f.file}>
                  <span className="font-medium text-ink">{f.label}</span>
                  <span className="block font-mono text-[11px] break-all text-faint">{f.file}</span>
                  <span className="block text-faint">{f.description}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <h3 className="mt-8 mb-2 text-[13px] font-semibold text-ink">In this chapter</h3>
      <ol className="grid gap-2 text-[13px]">
        {tutorial.steps.map((s, i) => (
          <li
            key={s.title}
            className="flex items-start gap-3 rounded-lg border border-line px-3 py-2"
          >
            <span className="w-8 pt-px font-mono text-[12px] text-accent">
              {number}.{i + 1}
            </span>
            <span className="flex-1">
              <span className="font-medium text-ink">{s.title}</span>
              <span className="mt-0.5 block text-xs text-faint">{ROLE_LABELS[s.role]}</span>
            </span>
          </li>
        ))}
      </ol>

      {tutorial.steps.map((step, i) => (
        <Step key={step.title} step={step} number={`${number}.${i + 1}`} />
      ))}
    </section>
  )
}

/**
 * Printable user manual built from the tutorials. Print it to A4 PDF ("Save as PDF") to refresh
 * frontend/public/tutorials/CRVR-User-Manual.pdf.
 */
export function ManualPage() {
  useLightTheme()
  return (
    <div className="min-h-screen bg-surface-3 [print-color-adjust:exact] print:bg-surface">
      <style>{PAGE_CSS}</style>
      <div className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-[210mm] items-center gap-4 px-4 py-3 text-[13px]">
          <Link
            to="/system/tutorials"
            className="inline-flex items-center gap-1 font-medium text-faint hover:text-accent"
          >
            <Icon name="chevron" strokeWidth={2} className="size-4 rotate-180" />
            Tutorials
          </Link>
          <span className="ml-auto text-faint">Printable manual · A4</span>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg border border-line-strong bg-surface px-3 py-1.5 font-semibold text-ink hover:bg-surface-2"
          >
            Print / Save as PDF
          </button>
        </div>
      </div>
      <main className="mx-auto my-6 max-w-[210mm] bg-surface px-[14mm] py-[14mm] shadow-lg print:my-0 print:max-w-none print:p-0 print:shadow-none">
        <Cover />
        <Introduction />
        <Contents />
        {TUTORIALS.map((t, i) => (
          <Chapter key={t.id} tutorial={t} number={i + 1} />
        ))}
      </main>
    </div>
  )
}
