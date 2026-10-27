import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function BoundaryPage() {
  return (
    <>
      <PageHeader title="Boundary" subtitle="Project boundary and overlap check" />
      <FeaturePlaceholder feature="F2" icon="map" title="Boundary map">
        Draw or upload the project polygon, then screen it against every registered boundary. An
        overlap above tolerance blocks issuance.
      </FeaturePlaceholder>
    </>
  )
}
