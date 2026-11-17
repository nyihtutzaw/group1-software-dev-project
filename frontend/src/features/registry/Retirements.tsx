import { Alert, Card, SectionHeader } from '@/components/ui'

import { date } from './format'
import { useRetirements } from './holdings-api'

/** Public retirement records of a batch: who the offset is claimed for, why and for which year. */
export function Retirements({ creditId }: { creditId: number }) {
  const retirements = useRetirements(creditId)

  return (
    <section aria-label="Retirements">
      <SectionHeader
        title="Retirements"
        action={
          retirements.data && (
            <span className="text-xs text-faint">
              {retirements.data.retired_quantity.toLocaleString()} of{' '}
              {retirements.data.quantity.toLocaleString()} tCO₂e retired
            </span>
          )
        }
      />
      {retirements.isError && (
        <Alert title="Could not load retirements">{retirements.error.message}</Alert>
      )}
      {retirements.data && (
        <Card className="overflow-hidden">
          {retirements.data.items.length === 0 ? (
            <p className="px-4 py-3 text-sm text-faint">
              No credits from this batch have been retired.
            </p>
          ) : (
            <ul>
              {retirements.data.items.map((item) => (
                <li
                  key={item.serial_block}
                  className="grid gap-1 border-b border-line px-4 py-3 text-sm last:border-b-0"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <b className="font-semibold text-ink">{item.beneficiary}</b>
                    <span className="text-faint">
                      {item.quantity.toLocaleString()} tCO₂e · reporting year {item.reporting_year}
                    </span>
                  </div>
                  <p className="text-muted">{item.reason}</p>
                  <p className="font-mono text-xs break-all text-faint">{item.serial_block}</p>
                  <time dateTime={item.retired_at} className="text-xs text-faint">
                    Retired {date(item.retired_at)}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </section>
  )
}
