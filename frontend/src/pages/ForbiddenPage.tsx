import { EmptyState, PageHeader } from '@/components/ui'

export function ForbiddenPage() {
  return (
    <>
      <PageHeader title="No access" />
      <EmptyState icon="lock" title="Your role cannot open this page">
        Ask a registry admin if you think you should have access.
      </EmptyState>
    </>
  )
}
