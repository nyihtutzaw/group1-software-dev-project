import type { ReactNode } from 'react'

import { EmptyState, type IconName, StatusChip } from '@/components/ui'

/**
 * Stand-in body for a page whose feature is not built yet.
 * Replace it with the real page content when you build the feature.
 */
export function FeaturePlaceholder({
  feature,
  icon,
  title,
  children,
}: {
  feature: string
  icon: IconName
  title: string
  children: ReactNode
}) {
  return (
    <EmptyState icon={icon} title={title}>
      <p>{children}</p>
      <p className="mt-3">
        <StatusChip tone="accent">{feature} · NOT BUILT YET</StatusChip>
      </p>
    </EmptyState>
  )
}
