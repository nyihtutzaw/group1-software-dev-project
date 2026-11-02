/**
 * Minimal JSON client for the backend. All calls go to /api on the same origin
 * (Vite proxies it in development), so the httpOnly session cookie is sent automatically.
 *
 *   const projects = await api.get<Project[]>('/projects')
 *   await api.post('/auth/login', { email, password })
 *   await api.upload<Result>('/boundaries/import', file)   // multipart, field "file"
 */

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type ValidationIssue = { loc?: (string | number)[]; msg?: string }

/** FastAPI sends a string, or for request validation a list of {loc, msg}: "area_ha: …". */
function errorDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail) || detail.length === 0) return null
  return (detail as ValidationIssue[])
    .map(({ loc, msg }) => {
      const field = loc?.at(-1)
      return typeof field === 'string' && field !== 'body' ? `${field}: ${msg}` : msg
    })
    .join('; ')
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData
  const res = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    // FormData sets its own multipart Content-Type (with boundary)
    headers: body === undefined || isForm ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new ApiError(res.status, errorDetail(data?.detail) ?? res.statusText)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, file: File, field = 'file') => {
    const form = new FormData()
    form.append(field, file)
    return request<T>('POST', path, form)
  },
}
