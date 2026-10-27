import { Link } from 'react-router'

import { EmptyState, PageHeader } from '@/components/ui'

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" />
      <EmptyState icon="search" title="There is nothing at this address">
        <Link to="/" className="font-semibold text-accent">
          Go to the home page
        </Link>
      </EmptyState>
    </>
  )
}
