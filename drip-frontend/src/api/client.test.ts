import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, refreshSession, request, setAccessToken } from './client'
import { formatPrice } from './types'

const json = (body: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })

afterEach(() => { setAccessToken(null) })

describe('API foundation', () => {
  it('uses credentials but does not leak bearer tokens to public requests', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ data: [] }))
    vi.stubGlobal('fetch', fetcher)
    setAccessToken('memory-only')
    await request('/products')
    const options = fetcher.mock.calls[0][1]
    expect(options.credentials).toBe('include')
    expect(options.headers.has('Authorization')).toBe(false)
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('preserves backend field errors, reference and retry delay', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({
      error: { code: 'RATE_LIMITED', message: 'Please wait.', fields: { email: 'Check email' }, request_id: 'req-123' },
    }, 429, { 'retry-after': '60' })))
    await expect(request('/auth/login', { method: 'POST' })).rejects.toMatchObject({
      status: 429, code: 'RATE_LIMITED', requestId: 'req-123', retryAfter: '60', fields: { email: 'Check email' },
    })
  })

  it('coalesces concurrent refresh calls', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ access_token: 'rotated' }))
    vi.stubGlobal('fetch', fetcher)
    expect(await Promise.all([refreshSession(), refreshSession()])).toEqual(['rotated', 'rotated'])
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('does not resurrect a cleared session from a late refresh', async () => {
    let complete!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise<Response>((resolve) => { complete = resolve })))
    const pending = refreshSession()
    setAccessToken(null)
    complete(json({ access_token: 'late' }))
    await expect(pending).rejects.toBeInstanceOf(ApiError)
  })

  it('refreshes an expired authenticated read exactly once', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(json({ error: { message: 'Expired' } }, 401))
      .mockResolvedValueOnce(json({ access_token: 'fresh' }))
      .mockResolvedValueOnce(json({ id: 'user-1' }))
    vi.stubGlobal('fetch', fetcher)
    setAccessToken('expired')
    expect(await request('/auth/me', { authenticated: true })).toEqual({ id: 'user-1' })
    expect(fetcher).toHaveBeenCalledTimes(3)
    expect(fetcher.mock.calls[2][1].headers.get('Authorization')).toBe('Bearer fresh')
  })

  it('does not automatically replay mutations', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ error: { message: 'Expired' } }, 401))
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/orders', { method: 'POST', authenticated: true })).rejects.toMatchObject({ status: 401 })
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('normalizes network failures without leaking implementation details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('private host details')))
    await expect(request('/products')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
  })

  it('supports no-content success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    expect(await request('/resource', { method: 'DELETE' })).toBeUndefined()
  })

  it('rejects non-JSON success instead of silently accepting a proxy error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Error</html>')))
    await expect(request('/products')).rejects.toMatchObject({ status: 502 })
  })

  it('does not permit an external request target', async () => {
    await expect(request('https://example.com')).rejects.toThrow('API-relative')
    await expect(request('//example.com')).rejects.toThrow('API-relative')
  })

  it('formats backend major units without dividing by 100', () => {
    expect(formatPrice('8900.00')).toBe('PKR 8,900')
    expect(formatPrice('12.50')).toBe('PKR 12.5')
    expect(formatPrice('not-money')).toBe('Price unavailable')
  })
})
