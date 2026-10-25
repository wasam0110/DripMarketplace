import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useOrderAccess } from '../orders/access'
import { RequestPreview } from '../orders/RequestPreview'
import { confirmReturn, type ReturnPayload, type ReturnReceipt } from '../orders/returns'
import { ReturnStatusPanel } from './ReturnPages'
import { OrderReviews } from '../reviews/OrderReviews'
import { isOrderId, orderDate, orderPath, statusLabel, useOrderRead, validateOrderDetail, validateOrders, type OrderDetail, type OrderItem } from '../orders/api'

function ReadError({ error, retry }: { error: unknown; retry: () => void }) {
  const inaccessible = error instanceof ApiError && [401, 403, 404].includes(error.status)
  return <><ErrorNotice error={inaccessible ? new Error('This order is unavailable with your current access. Sign in to the owning account, or use the correct private guest access code.') : error} />
    <Button className="button-secondary" onClick={retry}>Retry loading</Button></>
}

export function OrdersPage() {
  const auth = useAuth()
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  if (!auth.user || auth.error) return <section className="container page"><h1>Your orders</h1>
    {auth.error && <ErrorNotice error={new Error(auth.error)} />}
    <p>Sign in to see orders placed with your account.</p><Link className="button" to="/login">Sign in</Link>
    <p><Link to="/track">Track a guest order</Link></p></section>
  return <OrderHistory key={auth.user.id} />
}
function OrderHistory() {
  const [page, setPage] = useState(1)
  const resource = useOrderRead(`/orders?page=${page}`, true, validateOrders)
  return <section className="container page orders-page">
    <Link className="text-link" to="/account">Back to account</Link><p className="eyebrow">Your WearHowZ wardrobe</p><h1>Your orders</h1>
    <p className="lead">Each label, each piece, all in one place.</p>
    {resource.loading && <p role="status">Loading your orders…</p>}
    {Boolean(resource.error) && <ReadError error={resource.error} retry={resource.retry} />}
    {resource.data && <>
      {!resource.data.data.length ? <EmptyState title={page === 1 ? 'Your first order starts here.' : 'No orders on this page.'}><Link to="/clothing">Explore clothing</Link></EmptyState>
        : <ul className="order-history">{resource.data.data.map((order) => <li className="order-card" key={order.id}>
          <div><p className="eyebrow">{orderDate(order.created_at)}</p><h2><Link to={`/orders/${order.id}`}>{order.order_number}</Link></h2><p>{order.item_count} pieces · {statusLabel(order.status)}</p></div>
          <p>{formatPrice(order.total)}</p><Link className="text-link" to={`/orders/${order.id}`}>View order {order.order_number}</Link>
        </li>)}</ul>}
      <nav className="option-row" aria-label="Order pages">
        <Button className="button-secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous page</Button>
        <span role="status">Page {resource.data.pagination.page} of {resource.data.pagination.total_pages}</span>
        <Button className="button-secondary" disabled={page >= resource.data.pagination.total_pages} onClick={() => setPage((value) => value + 1)}>Next page</Button>
      </nav><Button className="button-secondary" onClick={resource.retry}>Refresh orders</Button>
    </>}
  </section>
}

export function OrderDetailPage() {
  const { id = '' } = useParams()
  const auth = useAuth()
  const { access } = useOrderAccess()
  if (!isOrderId(id)) return <section className="container page"><h1>Order unavailable</h1><Link to="/orders">Your orders</Link></section>
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  if (auth.error) return <section className="container page"><ErrorNotice error={new Error(auth.error)} /><Link to="/login">Sign in again</Link></section>
  if (!auth.user && access?.id !== id) return <GuestLookup key={id} initialIdentifier={id} />
  return <OrderRead key={`${auth.user?.id ?? 'guest'}:${id}`} path={orderPath(id)} authenticated={Boolean(auth.user)} token={!auth.user ? access?.token : undefined} />
}
export function GuestTrackingPage() {
  const auth = useAuth()
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  return <GuestLookup key={auth.user?.id ?? 'guest'} />
}
function GuestLookup({ initialIdentifier = '' }: { initialIdentifier?: string }) {
  const [identifier, setIdentifier] = useState(initialIdentifier)
  const [token, setToken] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [credentials, setCredentials] = useState<{ path: string; token: string } | null>(null)
  function submit(event: FormEvent) {
    event.preventDefault()
    try {
      if (!token.trim() || /\s/.test(token.trim())) throw new Error('Enter the complete private guest access code, without spaces.')
      setCredentials({ path: orderPath(identifier), token: token.trim() }); setToken(''); setError(null)
    } catch (reason) { setError(reason) }
  }
  if (credentials) return <><OrderRead key={`${credentials.path}:${credentials.token}`} path={credentials.path} token={credentials.token} authenticated={false} />
    <div className="container"><Button className="button-secondary" onClick={() => setCredentials(null)}>Use different guest details</Button></div></>
  return <section className="container page orders-page"><p className="eyebrow">Follow your pieces</p><h1>Track a guest order</h1>
    <p className="lead">Your order number alone cannot unlock private order details.</p>
    <form className="checkout-form guest-order-form" onSubmit={submit}>
      <Field label="Order number or ID" required maxLength={100} autoComplete="off" value={identifier} onChange={(event) => setIdentifier(event.target.value)} />
      <Field label="Private guest access code" type="password" required maxLength={4096} autoComplete="off" value={token} onChange={(event) => setToken(event.target.value)} />
      <p className="muted">This private code stays in memory and is sent only in a request header, never in the page address. An email address is not an access code.</p>
      {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit">View guest order</Button>
    </form><p>Just placed an order in this tab? <Link to="/checkout">Recover your recent checkout</Link>.</p>
    <Link className="text-link" to="/orders">Sign in for account order history</Link>
  </section>
}
function OrderRead({ path, authenticated, token }: { path: string; authenticated: boolean; token?: string }) {
  const resource = useOrderRead(path, authenticated, validateOrderDetail, token)
  // Keep the uncertain-write guard mounted while order reads refresh.
  const write = useAccountWrite()
  const [cancelled, setCancelled] = useState(false)
  const [returnReceipt, setReturnReceipt] = useState<ReturnReceipt | null>(null)
  const [showReturnStatus, setShowReturnStatus] = useState(false)
  const order = resource.data
  const eligible = Boolean(order && ['pending_payment', 'pending_cod_verification', 'processing'].includes(order.status)
    && order.seller_orders.every((shipment) => ['pending', 'processing'].includes(shipment.status)))
  const returnable = Boolean(order && ['delivered', 'completed'].includes(order.status))
  function submitReturn(payload: ReturnPayload) {
    if (!order || !returnable || returnReceipt || write.busy || write.blocked) return
    void write.run(async () => confirmReturn(await request<ReturnReceipt>(authenticated ? '/returns' : '/returns/guest', {
      method: 'POST', authenticated, headers: token ? { 'X-Guest-Token': token } : undefined,
      body: JSON.stringify(payload),
    }), order.id, payload), (receipt) => { setReturnReceipt(receipt); resource.retry() }, 'Return request received. Await approval and instructions before sending items back.')
  }
  function cancel(reason: string) {
    if (!order || !eligible || cancelled || write.busy || write.blocked || !reason.trim() || reason.trim().length > 500) return
    void write.run(async () => {
      const result = await request<{ message: string }>(`/orders/${order.id}/cancel`, {
        method: 'POST', authenticated, headers: token ? { 'X-Guest-Token': token } : undefined,
        body: JSON.stringify({ reason: reason.trim() }),
      })
      if (result?.message !== 'Order cancelled. Inventory has been released.') throw new Error('Cancellation could not be confirmed. Check order status before trying again.')
    }, () => { setCancelled(true); resource.retry() }, 'Order cancellation confirmed. No refund was issued by this action.')
  }
  return <section className="container page orders-page">
    <Link className="text-link" to={authenticated ? '/orders' : '/track'}>{authenticated ? 'All your orders' : 'Guest order access'}</Link>
    {resource.loading && <><h1>Your order</h1><p role="status">Loading order details…</p></>}
    {Boolean(resource.error) && <><h1>Order unavailable</h1><ReadError error={resource.error} retry={resource.retry} /></>}
    <WriteFeedback state={write} />
    {returnReceipt && <section className="account-card" aria-label="Return request confirmation"><h2>Return requested</h2>
      <p>Reference: {returnReceipt.id}</p><p>Submitted status: Requested. This is not approval or a refund.</p>
      <p>Keep this reference for support or future status lookup. Guest access codes are never saved by this page.</p>
      <p>Further return submissions are disabled on this page to prevent duplicates.</p>
      {authenticated ? <Link to={`/returns/${returnReceipt.id}`}>View current return status</Link> : <>
        <Button className="button-secondary" onClick={() => setShowReturnStatus(true)}>View current return status</Button>
        {showReturnStatus && <ReturnStatusPanel id={returnReceipt.id} authenticated={false} token={token} />}
        <p><Link to="/track-return">Guest return lookup</Link></p>
      </>}
    </section>}
    {resource.data && <><OrderView order={resource.data} />
      {!eligible && <p className="notice">This order cannot be cancelled here at its current shipment status. Contact support for paid orders or return assistance.</p>}
      <RequestPreview key={`request:${resource.data.id}`} order={resource.data} cancellation={{ disabled: !eligible || cancelled || write.busy || write.blocked, busy: write.busy, submit: cancel }} returns={{ disabled: !returnable || Boolean(returnReceipt) || write.busy || write.blocked, submit: submitReturn }} />
      {authenticated && <OrderReviews key={resource.data.id} order={resource.data} />}<Button className="button-secondary" disabled={write.busy} onClick={resource.retry}>Refresh order status</Button></>}
  </section>
}
function Items({ items }: { items: OrderItem[] }) {
  return <ul className="order-items">{items.map((item) => <li key={item.id}><h3>{item.product_name}</h3><p>{item.variant_label} · Qty {item.quantity}</p><p>{formatPrice(item.unit_price)} each · {formatPrice(item.subtotal)}</p></li>)}</ul>
}
function OrderView({ order }: { order: OrderDetail }) {
  const other = order.items.filter((item) => !order.seller_orders.some((shipment) => shipment.seller_id === item.seller_id))
  return <><p className="eyebrow">Placed {orderDate(order.created_at)}</p><h1>Order {order.order_number}</h1>
    <p role="status" className="lead">{statusLabel(order.status)}</p>
    {order.status === 'pending_cod_verification' && <p className="notice">Your COD order needs verification before processing. Check the checkout confirmation for the verification step.</p>}
    <div className="bag-layout"><div>
      <h2>Your shipments</h2><p>Each brand fulfils its own pieces. Shipment statuses can differ from the overall order status.</p>
      {order.seller_orders.map((shipment) => <article className="order-card shipment-card" key={shipment.id}>
        <h3>{shipment.brand_name}</h3><p>{statusLabel(shipment.status)}</p>
        <Items items={order.items.filter((item) => item.seller_id === shipment.seller_id)} />
        <dl><dt>Courier</dt><dd>{shipment.courier_name || 'Not assigned yet'}</dd><dt>Tracking number</dt><dd>{shipment.tracking_number || 'Not available yet'}</dd>
          {shipment.shipped_at && <><dt>Shipped</dt><dd>{orderDate(shipment.shipped_at)}</dd></>}
          {shipment.delivered_at && <><dt>Delivered</dt><dd>{orderDate(shipment.delivered_at)}</dd></>}
        </dl>
      </article>)}
      {other.length > 0 && <article className="order-card"><h3>Other ordered pieces</h3><Items items={other} /><p>Shipment details are not available.</p></article>}
      <h2>Delivery details</h2>{order.address ? <address>{order.address.recipient_name}<br />{order.address.street}<br />{order.address.city}, {order.address.province}<br />{order.address.phone}</address> : <p>Delivery address unavailable.</p>}
      {order.address?.note && <p>Delivery note: {order.address.note}</p>}{order.notes && <p>Order note: {order.notes}</p>}
    </div><aside className="bag-summary"><h2>Order summary</h2>
      <dl><div><dt>Subtotal</dt><dd>{formatPrice(order.subtotal)}</dd></div><div><dt>Discount</dt><dd>{formatPrice(order.discount_amount)}</dd></div><div><dt>Delivery</dt><dd>{formatPrice(order.shipping_fee)}</dd></div><div className="bag-total"><dt>Original total</dt><dd>{formatPrice(order.total)}</dd></div></dl>
      <p>Payment method: {order.payment_method === 'cod' ? 'Cash on delivery' : order.payment_method.replaceAll('_', ' ')}</p>
      <p className="muted">This is the original order total, not a refund or payment balance. Delivery estimates are not available yet.</p>
      <Link to="/help">Help with this order</Link>
    </aside></div>
  </>
}
