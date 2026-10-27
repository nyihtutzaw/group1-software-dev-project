---
name: frontend-code
description: Write CRVR frontend code the project's way — React 19 + TypeScript pages that match the HTML mock-up, the shared Tailwind UI kit and design tokens, role-guarded routes and menus, TanStack Query API calls, and Vitest tests. Use for any change under frontend/.
---

# Frontend code

React 19 · TypeScript (strict) · Vite · Tailwind CSS 4 · React Router · TanStack Query · Vitest +
Testing Library.

## The UI source of truth

`docs/project/CRVR-Mock-UI-v0.1.html` — open it in a browser. Every page you build should look like
its screen there: same structure, spacing, labels and states. The mock-up's CSS classes map to the
UI kit:

| Mock-up | Use |
|---|---|
| `.card` | `<Card>` |
| `.ph` / `.psub` | `<PageHeader title subtitle>` |
| `.sh h3` | `<SectionHeader title action>` |
| `.tile` / `.tiles` | `<StatTile>` in `<StatTiles>` |
| `.chip.c-ok/c-wait/c-warn/c-draft/c-acc` | `<StatusChip tone="ok/wait/warn/draft/accent">` |
| `.field` / `.two` | `<Field>` + `<Input/Select/Textarea>`, `<FieldRow>` |
| `.btn` / `.btn.ghost` / `.btn.danger` / `.btnrow` | `<Button variant>` / `<ButtonRow>` |
| `.alert` / `.alert.ok` | `<Alert tone="warn/ok" title>` |
| `.kv` | `<KeyValue items>` |
| icons | `<Icon name>` (add new paths to `components/ui/Icon.tsx`) |

Not in the kit yet (project rows `.prow`, file list `.file`, upload `.drop`, ledger rows, map
wrapper, checklist)? Build it **in your feature folder** first; move it to `components/ui/` when a
second feature needs it.

**Colours:** only design tokens (`bg-surface`, `text-muted`, `border-line`, `text-accent`,
`bg-warn-soft`, …, defined in `src/index.css`). No hex values in components. Dark mode then works
for free.
**Responsive:** design phone-first (≥ 420 px wide), then `desk:` (≥ 880 px) for the sidebar layout.

## Where things go

```
src/features/<feature>/   pages (XxxPage.tsx), feature components, api.ts, types.ts, tests
src/components/ui/        shared kit — change with care, mention in PR
src/layout/nav.ts         menu items + which roles see them (also drives route guards)
src/App.tsx               routes
src/lib/api.ts            fetch wrapper (api.get/post/…), throws ApiError(status, message)
src/auth/                 useAuth(), Guarded, Role types
```

New page: create it in `src/features/<feature>/`, add a route in `App.tsx` wrapped in
`<Guarded page="<nav id>">`, and a `NAV_ITEMS` entry in `layout/nav.ts` if it belongs in the menu.
Sub-pages (e.g. `/projects/:id`) reuse the parent's nav id in `Guarded`.

## Data fetching

Put a feature's API calls and hooks in `src/features/<feature>/api.ts`:

```ts
export type Project = { id: number; name: string; status: 'draft' | 'submitted' }

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: () => api.get<Project[]>('/projects') })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProjectIn) => api.post<Project>('/projects', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}
```

Types mirror the backend's Pydantic `…Out` schemas — keep the names the same. Handle the loading,
empty and error states on every page (`EmptyState`, `Alert`).

The current user: `const { user } = useAuth()` (`user.role` is one of `developer`, `verifier`,
`registry_staff`, `buyer`, `admin`). Hiding a button is UX only — the backend must enforce the rule.

## Tests

Next to the code: `XxxPage.test.tsx`. Use the helpers in `src/test/render.tsx`:

```tsx
mockFetch([{ id: 1, name: 'Nan Reforestation Phase II', status: 'submitted' }])
renderWithProviders(<HomePage />, { user: makeUser('developer') })
expect(await screen.findByText('Nan Reforestation Phase II')).toBeInTheDocument()
```

Query by role/label/text as a user would; don't test implementation details.

## Style

ESLint + Prettier (no semicolons, single quotes, width 100). Function components, named exports,
`@/` imports. Accessible markup: real `<button>`/`<a>`, `<label htmlFor>`, `aria-current` on nav.
