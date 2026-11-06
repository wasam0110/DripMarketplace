import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, statusLabel, useOrderRead } from '../orders/api'
import { adminOrderWarnings, validateAdminOrderDetail, type AdminOrderDetail } from './orders'
import { sellerMoney } from './sellers'
import { codMarker, codPayload, confirmCODOrder, confirmCODReceipt, matchCODOrder, sameCODReview, validateCODQueue, type CODAction, type CODQueueItem } from './cod'
import './products.css'

export function AdminCODPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>COD verification</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to review COD orders</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Cash on delivery</p><h1>{detail ? 'Review COD order' : 'COD verification queue'}</h1><p>Approval allows order preparation. It does not record cash collection, settle seller funds or issue a refund.</p>
    {detail ? isOrderId(id) ? <CODReview key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This COD order reference is invalid.</p> : <CODList key={user.id} />}
  </section>
}
function CODCard({ row, link = false }: { row: CODQueueItem; link?: boolean }) {
  return <section className="account-card"><h2>{row.order_number}</h2><dl><dt>Customer</dt><dd>{row.customer_name}</dd><dt>Saved contact phone</dt><dd>{row.customer_phone || 'Not recorded'}</dd><dt>Original checkout total</dt><dd>{sellerMoney(row.total)}</dd><dt>Brands</dt><dd>{row.brand_names.join(', ') || 'Not recorded'}</dd><dt>Placed</dt><dd>{orderDate(row.placed_at)}</dd><dt>Verification deadline (UTC)</dt><dd>{row.expires_at}</dd><dt>Minutes remaining at last read</dt><dd>{row.minutes_remaining}</dd></dl><p>Zero displayed minutes may mean less than one minute remains. The server rechecks the exact current deadline before approval.</p>{link && <Link className="text-link" to={`/admin/cod/${row.order_id}`}>Review COD {row.order_number}</Link>}</section>
}
function CODList() {
  const resource = useOrderRead('/admin/cod-queue', true, validateCODQueue)
  return <><p>Pending COD orders only, including expired records awaiting cancellation. This API returns the complete queue, without page totals.</p>{resource.loading && <p role="status">Loading COD queue...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{resource.data && <>{!resource.data.length && <EmptyState title="No orders awaiting COD verification"><p>Refresh later to check for new requests.</p></EmptyState>}{resource.data.map((row) => <CODCard key={row.order_id} row={row} link />)}</>}<Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh COD queue</Button></>
}
function CODReview({ owner, id }: { owner: string; id: string }) {
  const queue = useOrderRead('/admin/cod-queue', true, validateCODQueue), validate = useCallback((value: AdminOrderDetail) => validateAdminOrderDetail(value, id), [id])
  const orderPath = `/admin/orders/${id}`, resource = useOrderRead(orderPath, true, validate), write = useAccountWrite(), active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(codMarker(owner, id)) !== null } catch { return true } })
  const [now, setNow] = useState(Date.now)
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer) }, [])
  const row = queue.data?.find((item) => item.order_id === id), order = resource.data
  let match: AdminOrderDetail | null = null, error: unknown = null
  if (row && order) { try { match = matchCODOrder(row, order) } catch (reason) { error = reason } }
  const disabled = queue.loading || resource.loading || write.busy || write.blocked || pending
  function refresh() { queue.retry(); resource.retry() }
  function save(before: CODQueueItem, detail: AdminOrderDetail, action: CODAction, payload: ReturnType<typeof codPayload>) {
    if (disabled) return
    void write.run(async () => {
      let sent = false
      try {
        const [rows, current] = await Promise.all([request<CODQueueItem[]>('/admin/cod-queue', { authenticated: true, cache: 'no-store' }), request<AdminOrderDetail>(orderPath, { authenticated: true, cache: 'no-store' })])
        if (!active.current) throw new Error('The review session changed. No action was sent.')
        const latest = validateCODQueue(rows).find((item) => item.order_id === id)
        if (!latest || !sameCODReview(before, detail, latest, matchCODOrder(latest, validate(current)))) { refresh(); throw new Error('The order or COD deadline changed. Inspect the refreshed order before deciding.') }
        if (action === 'verify' && Date.now() >= Date.parse(latest.expires_at)) { refresh(); throw new Error('The COD deadline expired. Review cancellation instead.') }
        sessionStorage.setItem(codMarker(owner, id), 'pending'); setPending(true); sent = true
        confirmCODReceipt(await request<{ order_id: string; order_number: string; status: string; message: string }>(`/admin/cod-queue/${id}/${action}`, { authenticated: true, method: 'POST', body: JSON.stringify(payload) }), before, action)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The order could not be rechecked. No action was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(codMarker(owner, id)); setPending(false) }
        throw reason
      }
      try { confirmCODOrder(await request<AdminOrderDetail>(orderPath, { authenticated: true, cache: 'no-store' }), before, action, detail) }
      catch { throw new Error('The COD decision could not be confirmed. Inspect the order before repeating the action.') }
      sessionStorage.removeItem(codMarker(owner, id)); setPending(false)
    }, refresh, action === 'verify' ? 'COD order approved for preparation. No payment collection was recorded.' : 'COD order cancellation confirmed. No refund was issued.')
  }
  return <><p><Link className="text-link" to="/admin/cod">Back to COD queue</Link></p><p><Link className="text-link" to={`/admin/orders/${id}`}>Inspect full saved order</Link></p>{(queue.loading || resource.loading) && <p role="status">Loading COD review...</p>}{Boolean(queue.error) && <ErrorNotice error={queue.error} />}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{Boolean(error) && <ErrorNotice error={error} />}<WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A COD action is awaiting confirmation. Inspect the saved order or contact support before another action.</p>}
    {queue.data && !row && <p role="status">This order is no longer in the COD queue.</p>}{order && <p>Current saved order status: {statusLabel(order.status)}</p>}
    {row && <CODCard row={row} />}{match && <><section className="account-card"><h2>Saved delivery and items</h2>{match.address ? <address style={{ fontStyle: 'normal' }}>{match.address.recipient_name}<br />{match.address.phone}<br />{match.address.street}<br />{match.address.city}, {match.address.province}{match.address.note && <p>{match.address.note}</p>}</address> : <p>No saved delivery address.</p>}{match.notes && <p>Saved order note: {match.notes}</p>}{match.items.map((item) => <p key={item.id}>{item.product_name} · {item.variant_label} · {item.quantity} × {sellerMoney(item.unit_price)}</p>)}</section>
      {adminOrderWarnings(match).map((message) => <p role="alert" className="notice" key={message}>{message}</p>)}<CODForm key={`${row!.updated_at}:${row!.expires_at}`} row={row!} order={match} now={now} disabled={disabled} save={(action, payload) => save(row!, match!, action, payload)} />
    </>}<Button className="button-secondary" disabled={write.busy || queue.loading || resource.loading} onClick={refresh}>Refresh COD review and discard decision</Button></>
}
function CODForm({ row, order, now, disabled, save }: { row: CODQueueItem; order: AdminOrderDetail; now: number; disabled: boolean; save: (action: CODAction, payload: ReturnType<typeof codPayload>) => void }) {
  const expired = now >= Date.parse(row.expires_at), canVerify = !expired && !adminOrderWarnings(order).length && !!row.customer_phone.trim() && order.seller_orders.every((item) => item.status === 'pending')
  const [action, setAction] = useState<CODAction>(expired ? 'cancel' : 'verify'), [note, setNote] = useState(''), [checked, setChecked] = useState(false), [review, setReview] = useState<{ action: CODAction; payload: ReturnType<typeof codPayload> } | null>(null), [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled || review) return; try { if (action === 'verify' && !canVerify) throw new Error('Approval is unavailable. Inspect the saved order and deadline.'); setReview({ action, payload: codPayload(action, note, checked, row, now) }); setError(null) } catch (reason) { setError(reason) } }}>
    <h2>COD decision</h2>{expired && <p role="alert">The displayed COD deadline has expired. Approval is unavailable; the server checks its current policy.</p>}
    <div className="field"><label htmlFor="cod-action">Action</label><select id="cod-action" value={action} disabled={disabled || !!review} onChange={(event) => { setAction(event.target.value as CODAction); setChecked(false) }}><option value="verify" disabled={!canVerify}>Approve for preparation</option><option value="cancel">Cancel unverified order</option></select></div>
    <Field label={action === 'cancel' ? 'Cancellation reason' : 'Approval note (optional)'} value={note} maxLength={500} disabled={disabled || !!review} onChange={(event) => setNote(event.target.value)} hint={action === 'cancel' ? '10–500 characters. This is an order cancellation, not a refund.' : 'Up to 500 characters. This note does not confirm cash collection.'} />
    <label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={(event) => setChecked(event.target.checked)} /> {action === 'verify' ? 'I checked the customer contact and saved order details; this approves preparation only.' : 'I understand this cancels the order and releases reserved stock; it does not issue a refund.'}</label>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review || (action === 'verify' && !canVerify)}>Review COD action</Button>
    {review && <div className="admin-product-confirm"><h3>{review.action === 'verify' ? 'Approve order preparation?' : 'Cancel this COD order?'}</h3><p>{row.order_number} · {sellerMoney(row.total)}</p><p>Note: {review.payload.note || 'No note supplied'}</p><p>Order reference: {row.order_id}</p><div className="option-row"><Button disabled={disabled || (review.action === 'verify' && !canVerify)} onClick={() => save(review.action, review.payload)}>Confirm COD action</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to COD decision</Button></div></div>}
  </form>
}
