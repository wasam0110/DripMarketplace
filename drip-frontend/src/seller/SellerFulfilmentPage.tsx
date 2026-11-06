import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { validateSellerSummary } from './SellerStatus'
import { completeShippingAddress, confirmFulfilment, fulfilmentChange, fulfilmentLabel, fulfilmentMarker, nextFulfilment, validateFulfilmentDetail, validateFulfilmentPage, type FulfilmentChange, type FulfilmentDetail, type FulfilmentPage } from './fulfilment'

export function SellerFulfilmentPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id } = useParams()
  if (loading) return <section className="container page"><h1>Seller orders</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage fulfilment</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  if (detail && (!id || !isOrderId(id))) return <section className="container page"><h1>Invalid fulfilment link</h1><Link to="/seller/orders">Back to seller orders</Link></section>
  return <section className="container page account-page"><Link className="text-link" to={detail ? '/seller/orders' : '/seller'}>{detail ? 'Back to seller orders' : 'Back to seller workspace'}</Link><p className="eyebrow">WearHowZ · Your label</p><h1>{detail ? 'Fulfil an order' : 'Seller orders'}</h1><FulfilmentAccess key={`${user.id}:${detail ? id : 'list'}`} owner={user.id} id={detail ? id : undefined} /></section>
}
function FulfilmentAccess({ owner, id }: { owner: string; id?: string }) {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <>{resource.loading && <p role="status">Checking seller access…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && (resource.data.status === 'active' ? id ? <FulfilmentOrder key={resource.data.id} owner={owner} id={id} /> : <FulfilmentOrders key={resource.data.id} /> : <p>An active seller account is required to manage fulfilment.</p>)}
    {!resource.data && <Button disabled={resource.loading} onClick={resource.retry}>Retry seller access</Button>}</>
}
function FulfilmentOrders() {
  const [filter, setFilter] = useState('all'), [page, setPage] = useState(1)
  const validate = useCallback((value: FulfilmentPage) => validateFulfilmentPage(value, page, filter), [page, filter])
  const resource = useOrderRead(`/seller/orders?status=${filter}&page=${page}`, true, validate)
  return <>
    <p>Prepare and dispatch the items belonging to your brand. Payment and COD verification must be complete before fulfilment can begin.</p>
    <div className="field"><label htmlFor="fulfilment-filter">Fulfilment status</label><select id="fulfilment-filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}>
      <option value="all">All orders</option>{['pending', 'processing', 'shipped', 'delivered', 'cancelled'].map((value) => <option key={value} value={value}>{fulfilmentLabel(value)}</option>)}
    </select></div>
    {resource.loading && <p role="status">Loading seller orders…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>
      <p>{resource.data.pagination.total} matching orders</p>
      {!resource.data.data.length && <EmptyState title="No seller orders on this page"><p>Try another status or return to the previous page.</p></EmptyState>}
      {resource.data.data.map((row) => <article className="account-card" key={row.id}>
        <p className="eyebrow">{orderDate(row.created_at)}</p><h2>{row.order_number}</h2><p>{fulfilmentLabel(row.status)} · Brand items: {formatPrice(row.subtotal)}</p>
        <Link className="text-link" to={`/seller/orders/${row.id}`}>View fulfilment {row.order_number}</Link>
      </article>)}
      <p>Page {page} of {resource.data.pagination.total_pages}</p>
    </>}
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
      <Button className="button-secondary" disabled={resource.loading || page === 1} onClick={() => setPage(page - 1)}>Previous page</Button>
      <Button className="button-secondary" disabled={resource.loading || !resource.data || page >= resource.data.pagination.total_pages} onClick={() => setPage(page + 1)}>Next page</Button>
      <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh seller orders</Button>
    </div>
  </>
}
function FulfilmentOrder({ owner, id }: { owner: string; id: string }) {
  const validate = useCallback((value: FulfilmentDetail) => validateFulfilmentDetail(value, id), [id])
  const path = `/seller/orders/${id}`, resource = useOrderRead(path, true, validate), write = useAccountWrite()
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(fulfilmentMarker(owner, id)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || pending
  function save(before: FulfilmentDetail, change: FulfilmentChange) {
    if (disabled) return
    void write.run(async () => {
      sessionStorage.setItem(fulfilmentMarker(owner, id), 'pending'); setPending(true)
      try { await request(`${path}/status`, { authenticated: true, method: 'PUT', body: JSON.stringify(change) }) }
      catch (reason) {
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(fulfilmentMarker(owner, id)); setPending(false) }
        throw reason
      }
      let saved: FulfilmentDetail
      try { saved = confirmFulfilment(await request<FulfilmentDetail>(path, { authenticated: true, cache: 'no-store' }), before, change) }
      catch { throw new Error('The fulfilment update could not be confirmed. Refresh the order and resolve the change before trying again.') }
      sessionStorage.removeItem(fulfilmentMarker(owner, id)); setPending(false)
      return saved
    }, resource.retry, 'Fulfilment update saved and confirmed.')
  }
  const order = resource.data
  return <>
    {resource.loading && <p role="status">Loading fulfilment details…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {pending && !write.busy && <p role="alert">A fulfilment update is awaiting confirmation. Inspect the saved order or contact support to resolve it before making another change.</p>}
    {order && <>
      <div className="account-card"><h2>{order.order_number}</h2><p>{fulfilmentLabel(order.status)}</p><p>Brand item subtotal: {formatPrice(order.subtotal)}</p>
        <p>Placed {orderDate(order.created_at)}</p>
        {order.tracking_number && <p>Tracking number: {order.tracking_number}</p>}{order.courier_name && <p>Courier: {order.courier_name}</p>}
        {order.shipped_at && <p>Shipped {orderDate(order.shipped_at)}</p>}{order.delivered_at && <p>Delivered {orderDate(order.delivered_at)}</p>}
      </div>
      <section className="account-card"><h3>Ship to</h3><address style={{ fontStyle: 'normal', overflowWrap: 'anywhere' }}>{order.shipping_address.recipient_name}<br />{order.shipping_address.phone}<br />{order.shipping_address.street}<br />{order.shipping_address.city}, {order.shipping_address.province}</address>
        {!completeShippingAddress(order.shipping_address) && <p role="alert">The delivery address is incomplete. Contact support before updating fulfilment.</p>}
        {order.shipping_address.note && <p>Delivery note: {order.shipping_address.note}</p>}
        <p className="muted">Use these customer details only to fulfil this order.</p>
      </section>
      <section className="account-card"><h3>Your brand’s items</h3>{order.items.map((item, index) => <div key={index}><h4>{item.product_name}</h4><p>{item.variant_label} · {item.quantity} × {formatPrice(item.unit_price)} = {formatPrice(item.subtotal)}</p></div>)}</section>
      {nextFulfilment(order.status) ? <FulfilmentForm key={JSON.stringify(order)} order={order} disabled={disabled || resource.loading || !completeShippingAddress(order.shipping_address)} save={(change) => save(order, change)} /> : <p>No fulfilment action is available for this order.</p>}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh fulfilment and discard edits</Button>
  </>
}
function FulfilmentForm({ order, disabled, save }: { order: FulfilmentDetail; disabled: boolean; save: (change: FulfilmentChange) => void }) {
  const [tracking, setTracking] = useState(''), [courier, setCourier] = useState(''), [change, setChange] = useState<FulfilmentChange | null>(null), [error, setError] = useState<unknown>(null)
  const next = nextFulfilment(order.status)
  const label = next === 'processing' ? 'Start preparing' : next === 'shipped' ? 'Mark as shipped' : 'Confirm delivery'
  return <section className="account-card"><h3>{label}</h3>
    <form className="auth-form" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { setChange(fulfilmentChange(order, tracking, courier)); setError(null) } catch (reason) { setError(reason) } }}>
      {next === 'shipped' && <><Field label="Tracking number" required maxLength={100} value={tracking} disabled={disabled || !!change} onChange={(e) => setTracking(e.target.value)} /><Field label="Courier name" maxLength={100} value={courier} disabled={disabled || !!change} onChange={(e) => setCourier(e.target.value)} /></>}
      {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!change}>Review fulfilment update</Button>
    </form>
    {change && <div aria-label="Review fulfilment update"><h4>Review fulfilment update</h4><p>{change.status === 'processing' ? 'Confirm that your brand is preparing these items.' : change.status === 'shipped' ? `Confirm these items have been dispatched. Tracking: ${change.tracking_number}${change.courier_name ? ` · ${change.courier_name}` : ''}.` : 'Confirm that the customer has received these items. Delivery can start the earnings settlement process.'}</p>
      <Button disabled={disabled} onClick={() => save(change)}>Confirm fulfilment update</Button><Button className="button-secondary" disabled={disabled} onClick={() => setChange(null)}>Back to fulfilment edits</Button>
    </div>}
  </section>
}
