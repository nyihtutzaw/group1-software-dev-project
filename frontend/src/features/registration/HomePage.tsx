import { useAuth } from '@/auth/useAuth'
import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function HomePage() {
  const { user } = useAuth()
  const isDeveloper = user?.role === 'developer'

  return (
    <>
      <PageHeader
        title={isDeveloper ? 'My projects' : 'Overview'}
        subtitle={isDeveloper ? 'Projects you have registered' : 'Registry activity at a glance'}
      />
      <FeaturePlaceholder feature="F1" icon="home" title="Your projects will appear here">
        Registered projects with their status and progress, the stat tiles, and the monitoring-alert
        slot (satellite monitoring is deferred).
      </FeaturePlaceholder>
    </>
  )
}
