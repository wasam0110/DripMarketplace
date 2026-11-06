import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, statusLabel, useOrderRead } from '../orders/api'
import { fulfilmentLabel } from '../seller/fulfilment'
import { sellerMoney } from './sellers'
import { adminOrderQuery, adminOrderStatuses, adminOrderWarnings, paymentMethodLabel, validateAdminOrderDetail, validateAdminOrders, type AdminOrderDetail, type AdminOrders } from './orders'
import './products.css'

export function AdminOrdersPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Admin orders</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to inspect orders</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Order operations</p><h1>{detail ? 'Inspect order' : 'Admin orders'}</h1>
    <p>This is a read-only order view. COD verification, payment reconciliation, cancellation and refunds are separate operations.</p>
    {detail ? isOrderId(id) ? <OrderInspection key={`${user.id}:${id}`} id={id} /> : <p role="alert">This order reference is invalid.</p> : <OrderFilters key={user.id} />}
  </section>
}
function OrderFilters() {
  const [params, setParams] = useSearchParams(), status = params.get('status') ?? 'all', method = params.get('payment_method') ?? 'all', seller = params.get('seller_id') ?? '', page = params.get('page') ?? '1'
  const [draft, setDraft] = useState({ status, method, seller }), [formError, setFormError] = useState<unknown>(null)
  useEffect(() => { setDraft({ status, method, seller }); setFormError(null) }, [status, method, seller])
  let query = '', error: unknown = null
  try { query = adminOrderQuery(status, method, seller, page) } catch (reason) { error = reason }
  return <><form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); try { setParams(adminOrderQuery(draft.status, draft.method, draft.seller, '1')); setFormError(null) } catch (reason) { setFormError(reason) } }}>
    <div className="field"><label htmlFor="admin-order-status">Order status</label><select id="admin-order-status" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="all">All order statuses</option>{adminOrderStatuses.map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}</select></div>
    <div className="field"><label htmlFor="admin-order-payment">Payment method</label><select id="admin-order-payment" value={draft.method} onChange={(event) => setDraft({ ...draft, method: event.target.value })}><option value="all">All payment methods</option><option value="cod">Cash on delivery</option><option value="payfast">PayFast</option></select></div>
    <Field label="Seller reference (optional)" value={draft.seller} maxLength={36} onChange={(event) => setDraft({ ...draft, seller: event.target.value })} hint="Filters whole orders containing this brand; other brands and full order amounts remain visible." />
    <p>All payment methods includes historical records. Only COD and PayFast have individual filters.</p>{Boolean(formError) && <ErrorNotice error={formError} />}<Button type="submit">Apply order filters</Button>
  </form>{error ? <ErrorNotice error={error} /> : <OrderResults query={query} page={Number(page)} status={status} method={method} navigate={(next) => setParams(adminOrderQuery(status, method, seller, String(next)))} />}</>
}
function OrderResults({ query, page, status, method, navigate }: { query: string; page: number; status: string; method: string; navigate: (page: number) => void }) {
  const validate = useCallback((value: AdminOrders) => validateAdminOrders(value, page, status, method), [page, status, method])
  const resource = useOrderRead(`/admin/orders?${query}`, true, validate), data = resource.data
  return <>{resource.loading && <p role="status">Loading admin orders...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <>
    <section className="account-card"><h2>All matching orders</h2><dl><dt>Order count</dt><dd>{data.totals.order_count}</dd><dt>Original checkout totals</dt><dd>{sellerMoney(data.totals.total_gmv)}</dd><dt>Recorded net commission</dt><dd>{sellerMoney(data.totals.total_commission)}</dd></dl><p>These totals cover every matching page and the full parent orders, not just a selected brand. Checkout amounts can include unpaid, cancelled or refunded orders; they are not collected revenue. Net commission uses recorded settlement entries after commission reversals, not available cash or payouts.</p></section>
    <p role="status">Page {page} of {data.total_pages} · {data.total} matching orders</p>{!data.data.length && <EmptyState title="No orders on this page"><p>Change the filters or return to a previous page.</p></EmptyState>}
    {data.data.map((row) => <article className="account-card" key={row.id}><h2>{row.order_number}</h2><p>{statusLabel(row.status)} · {paymentMethodLabel(row.payment_method)}</p><p>{row.customer_name} · Placed {orderDate(row.created_at)}</p><dl><dt>Item subtotal</dt><dd>{sellerMoney(row.subtotal)}</dd><dt>Original checkout total</dt><dd>{sellerMoney(row.total)}</dd><dt>Recorded net commission</dt><dd>{sellerMoney(row.commission)}</dd><dt>Brand fulfilment records</dt><dd>{row.seller_count}</dd></dl><Link className="text-link" to={`/admin/orders/${row.id}`}>Inspect {row.order_number}</Link></article>)}
  </>}<div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous order page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= data.total_pages} onClick={() => navigate(page + 1)}>Next order page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh admin orders</Button></div></>
}
function OrderInspection({ id }: { id: string }) {
  const validate = useCallback((value: AdminOrderDetail) => validateAdminOrderDetail(value, id), [id])
  const resource = useOrderRead(`/admin/orders/${id}`, true, validate), order = resource.data
  return <><p><Link className="text-link" to="/admin/orders">Back to admin orders</Link></p>{resource.loading && <p role="status">Loading order detail...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{order && <>
    {adminOrderWarnings(order).map((message) => <p className="notice" role="alert" key={message}>{message} No records have been changed.</p>)}
    <section className="account-card"><h2>{order.order_number}</h2><dl><dt>Order status</dt><dd>{statusLabel(order.status)}</dd><dt>Payment method recorded</dt><dd>{paymentMethodLabel(order.payment_method)}</dd><dt>Customer name</dt><dd>{order.customer_name}</dd><dt>Account reference</dt><dd>{order.user_id || 'Not linked to an account'}</dd><dt>Placed</dt><dd>{orderDate(order.created_at)}</dd><dt>Order reference</dt><dd>{order.id}</dd><dt>Saved order note</dt><dd className="admin-product-copy">{order.notes || 'No note supplied'}</dd></dl><p>Order status and method are not a provider payment receipt or a refund reconciliation record.</p></section>
    <section className="account-card"><h2>Saved checkout amounts</h2><dl><dt>Item subtotal</dt><dd>{sellerMoney(order.subtotal)}</dd><dt>Discount</dt><dd>{sellerMoney(order.discount_amount)}</dd><dt>Shipping fee</dt><dd>{sellerMoney(order.shipping_fee)}</dd><dt>Original checkout total</dt><dd>{sellerMoney(order.total)}</dd><dt>Recorded net commission</dt><dd>{sellerMoney(order.commission)}</dd></dl><p>Original checkout values are not recalculated from today's catalogue. Recorded net commission is after commission reversals; it does not prove collection, payout or completion of a customer refund.</p></section>
    <section className="account-card"><h2>Saved delivery address</h2>{order.address ? <address style={{ fontStyle: 'normal' }}>{order.address.recipient_name}<br />{order.address.phone}<br />{order.address.street}<br />{order.address.city}, {order.address.province}{order.address.note && <p className="admin-product-copy">Delivery note: {order.address.note}</p>}</address> : <p>No saved delivery address.</p>}<p>Use these private details only for authorised order operations.</p></section>
    <section className="account-card"><h2>Saved order items</h2>{!order.items.length && <p>No saved item snapshots.</p>}{order.items.map((item) => <article className="admin-product-variant" key={item.id}><h3>{item.product_name}</h3><p>{item.variant_label || 'No variant label supplied'}</p><p>{item.quantity} × {sellerMoney(item.unit_price)} = {sellerMoney(item.subtotal)}</p><p>Seller reference: {item.seller_id}</p><p><Link className="text-link" to={`/admin/products/${item.product_id}`}>Inspect current product {item.product_id}</Link></p><p className="muted">The current product may be changed or archived; these are the saved checkout details.</p></article>)}</section>
    <section className="account-card"><h2>Brand fulfilment</h2>{!order.seller_orders.length && <p>No saved brand fulfilment records.</p>}{order.seller_orders.map((row) => <article className="admin-product-variant" key={row.id}><h3>{row.brand_name || 'Brand name unavailable'}</h3><dl><dt>Fulfilment status</dt><dd>{fulfilmentLabel(row.status)}</dd><dt>Brand item subtotal</dt><dd>{sellerMoney(row.subtotal)}</dd><dt>Tracking number</dt><dd>{row.tracking_number || 'Not supplied'}</dd><dt>Courier</dt><dd>{row.courier_name || 'Not supplied'}</dd><dt>Shipped</dt><dd>{row.shipped_at ? orderDate(row.shipped_at) : 'Not recorded'}</dd><dt>Delivered</dt><dd>{row.delivered_at ? orderDate(row.delivered_at) : 'Not recorded'}</dd><dt>Fulfilment reference</dt><dd>{row.id}</dd></dl><Link className="text-link" to={`/admin/sellers/${row.seller_id}`}>Inspect brand {row.seller_id}</Link></article>)}</section>
  </>}<Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh order detail</Button></>
}
