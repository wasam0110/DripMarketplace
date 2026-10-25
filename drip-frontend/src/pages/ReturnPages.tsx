import { useCallback, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { AccountGate } from '../account/AccountDetails'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { returnStatus, validateReturnDetail, validateReturnList, type ReturnDetail, type ReturnList } from '../orders/returnHistory'

function ReturnError({ error }: { error: unknown }) {
  return <ErrorNotice error={error instanceof ApiError && [401, 403, 404].includes(error.status)
    ? new Error('This return is unavailable with your current access. Use the owning account or matching private guest code.') : error} />
}
export function ReturnsPage() {
  return <><AccountGate title="Your returns">{(owner) => <ReturnHistory key={owner} />}</AccountGate>
    <p className="container"><Link to="/track-return">Track a guest return</Link></p></>
}
function ReturnHistory() {
  const [page, setPage] = useState(1)
  const validate = useCallback((value: ReturnList) => validateReturnList(value, page), [page])
  const resource = useOrderRead(`/returns?page=${page}`, true, validate)
  return <>
    <p>Each request belongs to one brand shipment. Statuses are supplied by the backend, not estimates.</p>
    {resource.loading && <p role="status">Loading returns…</p>}
    {Boolean(resource.error) && <ReturnError error={resource.error} />}
    {resource.data && <>
      {!resource.data.data.length && <p>{page === 1 ? 'No return requests yet.' : 'No returns on this page.'}</p>}
      <ul className="order-history">{resource.data.data.map((row) => <li className="order-card" key={row.id}>
        <h2>{returnStatus(row.status).label}</h2><p>Reference: {row.id}</p>
        <p>{orderDate(row.requested_at)} · {row.item_count} item lines</p>
        <Link to={`/returns/${row.id}`}>View return {row.id}</Link>
      </li>)}</ul>
      <nav className="option-row" aria-label="Return pages">
        <Button disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous page</Button>
        <span>Page {page} of {resource.data.total_pages}</span>
        <Button disabled={page >= resource.data.total_pages} onClick={() => setPage((value) => value + 1)}>Next page</Button>
      </nav>
    </>}
    <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh returns</Button>
    <p><Link to="/orders">View orders to request a return</Link></p>
  </>
}
export function ReturnDetailPage() {
  const { id = '' } = useParams()
  if (!isOrderId(id)) return <section className="container page"><h1>Return unavailable</h1><Link to="/returns">Your returns</Link></section>
  return <AccountGate title="Return details">{(owner) => <ReturnStatusPanel key={`${owner}:${id}`} id={id} authenticated />}</AccountGate>
}
/** Shared read-only status view; no guest token goes into navigation or storage. */
export function ReturnStatusPanel({ id, authenticated, token }: { id: string; authenticated: boolean; token?: string }) {
  const validate = useCallback((value: ReturnDetail) => validateReturnDetail(value, id), [id])
  const resource = useOrderRead(`/returns/${authenticated ? '' : 'guest/'}${id}`, authenticated, validate, token)
  const detail = resource.data
  return <section aria-label="Current return status">
    {resource.loading && <p role="status">Loading return details…</p>}
    {Boolean(resource.error) && <ReturnError error={resource.error} />}
    {detail && <article className="account-card">
      <h2>{returnStatus(detail.status).label}</h2><p>{returnStatus(detail.status).description}</p>
      <p>Reference: {detail.id}</p><p>Requested: {orderDate(detail.requested_at)}</p>
      {detail.resolved_at && <p>Resolved: {orderDate(detail.resolved_at)}</p>}
      <h3>Your reason</h3><p className="request-reason">{detail.reason}</p>
      {detail.notes && <><h3>Notes</h3><p className="request-reason">{detail.notes}</p></>}
      <h3>Requested items</h3><p className="muted">The return API supplies item references, not product names.</p>
      <ul className="order-items">{detail.items.map((item) => <li key={item.id}><p>Order item: {item.order_item_id}</p><p>Quantity: {item.quantity}</p>{item.reason && <p>{item.reason}</p>}</li>)}</ul>
      {authenticated && <Link to={`/orders/${detail.order_id}`}>View original order</Link>}
      {authenticated ? <p><Link to={`/returns/${id}/dispute`}>View or open a dispute</Link></p> : detail.status === 'rejected' && <p>Guest disputes are not supported by the current API. Contact support for help with this return.</p>}
    </article>}
    <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh return status</Button>
    {authenticated && <p><Link to="/returns">All your returns</Link></p>}
  </section>
}
export function GuestReturnPage() {
  const auth = useAuth()
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  return <GuestReturnLookup key={auth.user?.id ?? 'guest'} />
}
function GuestReturnLookup() {
  const [id, setId] = useState('')
  const [token, setToken] = useState('')
  const [credentials, setCredentials] = useState<{ id: string; token: string } | null>(null)
  const [error, setError] = useState<unknown>(null)
  function lookup(event: FormEvent) {
    event.preventDefault()
    if (!isOrderId(id.trim()) || !token.trim() || /\s/.test(token.trim())) { setError(new Error('Enter a valid return reference and complete private guest code.')); return }
    setCredentials({ id: id.trim(), token: token.trim() }); setId(''); setToken(''); setError(null)
  }
  return <section className="container page"><h1>Track a guest return</h1>
    <p>Use the return reference and the private access code for its original guest order. Your order number alone cannot unlock a return.</p>
    {credentials ? <><ReturnStatusPanel key={`${credentials.id}:${credentials.token}`} id={credentials.id} token={credentials.token} authenticated={false} />
      <Button className="button-secondary" onClick={() => setCredentials(null)}>Use different guest details</Button></>
      : <form className="checkout-form" onSubmit={lookup}>
        <Field label="Return reference" required autoComplete="off" maxLength={36} value={id} onChange={(event) => setId(event.target.value)} />
        <Field label="Private guest access code" type="password" required autoComplete="off" maxLength={4096} value={token} onChange={(event) => setToken(event.target.value)} />
        <p className="muted">Your code stays in memory and is sent only in a request header. Reloading clears access.</p>
        {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit">View guest return</Button>
      </form>}
    <p><Link to="/returns">Account return history</Link></p>
  </section>
}
