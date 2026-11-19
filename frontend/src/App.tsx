import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router'

import { Guarded } from '@/auth/Guarded'
import { LedgerPage } from '@/features/audit/LedgerPage'
import { RolesAccessPage } from '@/features/audit/RolesAccessPage'
import { UsersPage } from '@/features/audit/UsersPage'
import { HomePage } from '@/features/registration/HomePage'
import { ProjectPage } from '@/features/registration/ProjectPage'
import { SubmitPage } from '@/features/registration/SubmitPage'
import { AccessPage } from '@/features/registry/AccessPage'
import { CreditPage } from '@/features/registry/CreditPage'
import { RegistryPage } from '@/features/registry/RegistryPage'
import { ReviewPage } from '@/features/verification/ReviewPage'
import { VerifyPage } from '@/features/verification/VerifyPage'
import { AppShell } from '@/layout/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// Map libraries are large; load the boundary page only when it is opened.
const BoundaryPage = lazy(() =>
  import('@/features/boundary/BoundaryPage').then((m) => ({ default: m.BoundaryPage })),
)

// Tutorials carry long text and screenshot lists; load them only when an admin opens one.
const TutorialsPage = lazy(() =>
  import('@/features/tutorials/TutorialsPage').then((m) => ({ default: m.TutorialsPage })),
)
const TutorialPage = lazy(() =>
  import('@/features/tutorials/TutorialPage').then((m) => ({ default: m.TutorialPage })),
)

// Every page route is guarded by its entry in layout/nav.ts (roles + public flag).
// Feature sub-pages (e.g. /projects/:id) go here too, guarded by their parent's id.
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route
          index
          element={
            <Guarded page="home">
              <HomePage />
            </Guarded>
          }
        />
        <Route
          path="/projects/new"
          element={
            <Guarded page="submit">
              <SubmitPage />
            </Guarded>
          }
        />
        <Route
          path="/projects/:id/edit"
          element={
            <Guarded page="submit">
              <SubmitPage />
            </Guarded>
          }
        />
        <Route
          path="/projects/:id"
          element={
            <Guarded page="home">
              <ProjectPage />
            </Guarded>
          }
        />
        <Route
          path="/boundary"
          element={
            <Guarded page="map">
              <Suspense fallback={<p className="text-sm text-faint">Loading map…</p>}>
                <BoundaryPage />
              </Suspense>
            </Guarded>
          }
        />
        <Route
          path="/verify"
          element={
            <Guarded page="verify">
              <VerifyPage />
            </Guarded>
          }
        />
        <Route
          path="/verify/:id"
          element={
            <Guarded page="verify">
              <ReviewPage />
            </Guarded>
          }
        />
        <Route
          path="/registry/:id"
          element={
            <Guarded page="registry">
              <CreditPage />
            </Guarded>
          }
        />
        <Route
          path="/registry"
          element={
            <Guarded page="registry">
              <RegistryPage />
            </Guarded>
          }
        />
        <Route
          path="/buyer-access"
          element={
            <Guarded page="access">
              <AccessPage />
            </Guarded>
          }
        />
        <Route
          path="/ledger"
          element={
            <Guarded page="ledger">
              <LedgerPage />
            </Guarded>
          }
        />
        <Route
          path="/admin/users"
          element={
            <Guarded page="users">
              <UsersPage />
            </Guarded>
          }
        />
        <Route
          path="/system/roles-access"
          element={
            <Guarded page="roles-access">
              <RolesAccessPage />
            </Guarded>
          }
        />
        <Route
          path="/system/tutorials"
          element={
            <Guarded page="tutorials">
              <Suspense fallback={<p className="text-sm text-faint">Loading tutorial…</p>}>
                <TutorialsPage />
              </Suspense>
            </Guarded>
          }
        />
        <Route
          path="/system/tutorials/:id"
          element={
            <Guarded page="tutorials">
              <Suspense fallback={<p className="text-sm text-faint">Loading tutorial…</p>}>
                <TutorialPage />
              </Suspense>
            </Guarded>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
