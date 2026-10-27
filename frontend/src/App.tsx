import { Route, Routes } from 'react-router'

import { Guarded } from '@/auth/Guarded'
import { LedgerPage } from '@/features/audit/LedgerPage'
import { UsersPage } from '@/features/audit/UsersPage'
import { BoundaryPage } from '@/features/boundary/BoundaryPage'
import { HomePage } from '@/features/registration/HomePage'
import { SubmitPage } from '@/features/registration/SubmitPage'
import { RegistryPage } from '@/features/registry/RegistryPage'
import { VerifyPage } from '@/features/verification/VerifyPage'
import { AppShell } from '@/layout/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

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
          path="/boundary"
          element={
            <Guarded page="map">
              <BoundaryPage />
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
          path="/registry"
          element={
            <Guarded page="registry">
              <RegistryPage />
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
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
