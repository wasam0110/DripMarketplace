export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code = 'REQUEST_FAILED',
    public fields: Record<string, string> = {},
    public requestId?: string,
    public retryAfter?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

// Access tokens stay in memory. The backend owns the HttpOnly refresh cookie.
let accessToken: string | null = null
let sessionVersion = 0
let refreshRequest: Promise<string> | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
  sessionVersion += 1
}

export async function refreshSession(): Promise<string> {
  if (refreshRequest) return refreshRequest
  const version = sessionVersion
  refreshRequest = request<{ access_token: string }>('/auth/refresh', { method: 'POST' })
    .then(({ access_token }) => {
      if (version !== sessionVersion) {
        throw new ApiError('Your session has changed. Please sign in again.', 401)
      }
      accessToken = access_token
      return access_token
    })
    .catch((error: unknown) => {
      if (version === sessionVersion && error instanceof ApiError && error.status === 401) {
        setAccessToken(null)
      }
      throw error
    })
    .finally(() => { refreshRequest = null })
  return refreshRequest
}

type RequestOptions = RequestInit & { authenticated?: boolean }

/** Send JSON to our backend; refresh only authenticated GETs, never replay writes. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { authenticated = false, ...init } = options
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use an API-relative path.')
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (authenticated && accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const send = () => fetch(`${API_BASE}${path}`, {
    ...init, headers, credentials: 'include', signal: init.signal ?? AbortSignal.timeout(15000),
  })
  let response: Response
  try {
    response = await send()
    if (response.status === 401 && authenticated && (init.method ?? 'GET') === 'GET') {
      headers.set('Authorization', `Bearer ${await refreshSession()}`)
      response = await send()
    }
  } catch (error) {
    if (init.signal?.aborted || error instanceof ApiError) throw error
    throw new ApiError('We couldn’t connect. Check your connection and try again.', 0, 'NETWORK_ERROR')
  }
  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.error
    throw new ApiError(
      typeof detail?.message === 'string' ? detail.message : 'We couldn’t complete that request.',
      response.status,
      typeof detail?.code === 'string' ? detail.code : 'REQUEST_FAILED',
      detail?.fields ?? {},
      detail?.request_id ?? response.headers.get('x-request-id') ?? undefined,
      response.headers.get('retry-after') ?? undefined,
    )
  }
  if (payload === null) throw new ApiError('The server returned an unexpected response.', 502)
  return payload as T
}
