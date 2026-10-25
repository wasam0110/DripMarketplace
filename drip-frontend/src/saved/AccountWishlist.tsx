import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice } from '../components/ui'
import { useSaved } from './SavedProvider'

interface Item { product_id: string; product_name: string; price: string; sale_price: string | null; is_in_stock: boolean }
interface Wishlist { items: Item[]; total: number }
function validate(value: Wishlist): Wishlist {
  if (!value || !Array.isArray(value.items) || !Number.isSafeInteger(value.total) || value.total !== value.items.length || value.items.some((item) =>
    !item || typeof item.product_id !== 'string' || !/^[0-9a-f-]{36}$/i.test(item.product_id) || typeof item.product_name !== 'string' ||
    typeof item.price !== 'string' || (item.sale_price !== null && typeof item.sale_price !== 'string') || typeof item.is_in_stock !== 'boolean') ||
    new Set(value.items.map((item) => item.product_id)).size !== value.items.length) throw new Error('The account wishlist response was incomplete. Refresh before making changes.')
  return value
}

export function AccountWishlist() {
  const auth = useAuth()
  if (auth.loading) return <p role="status">Checking your account…</p>
  if (!auth.user) return <p><Link className="text-link" to="/login">Sign in</Link> to manage an account wishlist. Device saves are never copied automatically.</p>
  return <AccountList key={auth.user.id} />
}

function AccountList() {
  const saved = useSaved()
  const [data, setData] = useState<Wishlist | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const [generation, setGeneration] = useState(0)
  const lock = useRef(false)
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    const controller = new AbortController()
    setBusy(true); setData(null); setError(null)
    request<Wishlist>('/me/wishlist', { authenticated: true, cache: 'no-store', signal: controller.signal })
      .then(validate).then((value) => { if (!controller.signal.aborted) setData(value) })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason) })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => controller.abort()
  }, [generation])

  async function change(id: string, add: boolean) {
    if (lock.current || busy || uncertain || !data) return
    lock.current = true; setBusy(true); setError(null); setNotice('')
    try {
      if (add) {
        const result = validate(await request<Wishlist>('/me/wishlist', { authenticated: true, method: 'POST', body: JSON.stringify({ product_id: id }) }))
        if (!mounted.current) return
        setData(result)
        setNotice(result.items.some((item) => item.product_id === id) ? 'Saved to your account. Your device copy is unchanged.' : 'Request accepted, but this piece is not currently visible in your account wishlist.')
      } else {
        const result = await request<unknown>(`/me/wishlist/${encodeURIComponent(id)}`, { authenticated: true, method: 'DELETE' })
        if (result !== undefined) throw new Error('Unexpected removal response.')
        if (!mounted.current) return
        setData({ items: data.items.filter((item) => item.product_id !== id), total: data.total - 1 })
        setNotice('Removed from your account wishlist. Device saves are unchanged.')
      }
    } catch (reason) {
      if (!mounted.current) return
      setError(reason)
      if (!(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500) {
        setUncertain(true)
        setNotice('The change may have reached the server. Refresh to inspect the list; do not repeat the change until resolved. Changes stay locked on this page.')
      }
    } finally { lock.current = false; if (mounted.current) setBusy(false) }
  }
  return <section aria-labelledby="account-wishlist-heading">
    <h2 id="account-wishlist-heading">Account wishlist</h2>
    <p>Separate from this browser’s saved pieces. Available on your signed-in devices; the server list expires 90 days after its latest addition. Unavailable products are omitted. Saving does not reserve stock or prices.</p>
    <Button className="button-secondary" disabled={busy} onClick={() => setGeneration((value) => value + 1)}>Refresh account wishlist</Button>
    {busy && <p role="status">Updating account wishlist…</p>}
    {Boolean(error) && <ErrorNotice error={error} />}
    <p role="status">{notice}</p>
    {data && <>
      {!data.items.length && <p>No available pieces in your account wishlist.</p>}
      <ul className="order-items">{data.items.map((item) => <li key={item.product_id}>
        <h3><Link to={`/products/${encodeURIComponent(item.product_id)}`}>{item.product_name}</Link></h3>
        <p>{formatPrice(item.sale_price ?? item.price)} · {item.is_in_stock ? 'In stock when loaded' : 'Out of stock'}</p>
        <Button className="button-secondary" disabled={busy || uncertain} onClick={() => change(item.product_id, false)}>Remove {item.product_name} from account</Button>
      </li>)}</ul>
      {saved.ready && !saved.error && saved.ids.some((id) => !data.items.some((item) => item.product_id === id)) && <>
        <h3>Copy a device save to your account</h3><p>Copy only the pieces you choose. Device saves stay in this browser.</p>
        <ul>{saved.ids.filter((id) => !data.items.some((item) => item.product_id === id)).map((id, index) => <li key={id}>
          <Link className="text-link" to={`/products/${encodeURIComponent(id)}`}>View device piece {index + 1}</Link>{' '}
          <Button className="button-secondary" disabled={busy || uncertain} onClick={() => change(id, true)}>Copy device piece {index + 1} to account</Button>
        </li>)}</ul>
      </>}
    </>}
  </section>
}
