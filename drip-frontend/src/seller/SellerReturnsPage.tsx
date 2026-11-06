import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { type ReturnList } from '../orders/returnHistory'
import { validateSellerSummary } from './SellerStatus'
import { confirmSellerReturn, sellerReturnActions, sellerReturnBody, sellerReturnLabel, sellerReturnMarker, validateSellerReturn, validateSellerReturns, type SellerReturnAction, type SellerReturnDetail } from './returns'

export function SellerReturnsPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id } = useParams()
  if (loading) return <section className="container page"><h1>Seller returns</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage returns</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  if (detail && (!id || !isOrderId(id))) return <section className="container page"><h1>Invalid return link</h1><Link to="/seller/returns">Back to seller returns</Link></section>
  return <section className="container page account-page" style={{ overflowWrap: 'anywhere' }}><Link className="text-link" to={detail ? '/seller/returns' : '/seller'}>{detail ? 'Back to seller returns' : 'Back to seller workspace'}</Link><p className="eyebrow">WearHowZ · Your label</p><h1>{detail ? 'Review a return' : 'Seller returns'}</h1><ReturnAccess key={`${user.id}:${detail ? id : 'list'}`} owner={user.id} id={detail ? id : undefined} /></section>
}
function ReturnAccess({ owner, id }: { owner: string; id?: string }) {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <>{resource.loading && <p role="status">Checking seller access…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && (resource.data.status === 'active' ? id ? <ReturnManager key={resource.data.id} owner={owner} id={id} /> : <ReturnQueue key={resource.data.id} /> : <p>An active seller account is required to manage returns.</p>)}
    {!resource.data && <Button disabled={resource.loading} onClick={resource.retry}>Retry seller access</Button>}</>
}
function ReturnQueue() {
  const [filter, setFilter] = useState(''), [page, setPage] = useState(1)
  const validate = useCallback((value: ReturnList) => validateSellerReturns(value, page, filter), [page, filter])
  const resource = useOrderRead(`/seller/returns?page=${page}${filter ? `&status=${filter}` : ''}`, true, validate)
  return <>
    <p>Review return requests for your brand and record when approved items arrive.</p>
    <div className="field"><label htmlFor="seller-return-status">Return status</label><select id="seller-return-status" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}><option value="">All returns</option>{['requested', 'approved', 'rejected', 'received', 'refunded'].map((status) => <option key={status} value={status}>{sellerReturnLabel(status)}</option>)}</select></div>
    {resource.loading && <p role="status">Loading seller returns…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>
      <p>{resource.data.total} matching returns</p>
      {!resource.data.data.length && <EmptyState title="No seller returns on this page"><p>Try another status or return to the previous page.</p></EmptyState>}
      {resource.data.data.map((row) => <article className="account-card" key={row.id} style={{ overflowWrap: 'anywhere' }}><p className="eyebrow">{orderDate(row.requested_at)}</p><h2>{sellerReturnLabel(row.status)}</h2><p>Reference: {row.id}</p><p>{row.item_count} item lines · {row.reason}</p><Link className="text-link" to={`/seller/returns/${row.id}`}>Review return {row.id}</Link></article>)}
      <p>Page {page} of {resource.data.total_pages}</p>
    </>}
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}><Button className="button-secondary" disabled={resource.loading || page === 1} onClick={() => setPage(page - 1)}>Previous page</Button><Button className="button-secondary" disabled={resource.loading || !resource.data || page >= resource.data.total_pages} onClick={() => setPage(page + 1)}>Next page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh seller returns</Button></div>
  </>
}
function ReturnManager({ owner, id }: { owner: string; id: string }) {
  const validate = useCallback((value: SellerReturnDetail) => validateSellerReturn(value, id), [id])
  const path = `/seller/returns/${id}`, resource = useOrderRead(path, true, validate), write = useAccountWrite()
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(sellerReturnMarker(owner, id)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || pending
  function save(before: SellerReturnDetail, action: SellerReturnAction, body: { admin_note?: string }) {
    if (disabled || !sellerReturnActions(before).includes(action)) return
    void write.run(async () => {
      sessionStorage.setItem(sellerReturnMarker(owner, id), 'pending'); setPending(true)
      try { await request(`${path}/${action === 'mark_received' ? 'received' : action}`, { authenticated: true, method: 'POST', body: JSON.stringify(body) }) }
      catch (reason) { if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(sellerReturnMarker(owner, id)); setPending(false) }; throw reason }
      let saved: SellerReturnDetail
      try { saved = confirmSellerReturn(await request<SellerReturnDetail>(path, { authenticated: true, cache: 'no-store' }), before, action, body) }
      catch { throw new Error('The return update could not be confirmed. Inspect the return or contact support before trying again.') }
      sessionStorage.removeItem(sellerReturnMarker(owner, id)); setPending(false)
      return saved
    }, resource.retry, 'Return update saved and confirmed.')
  }
  const returned = resource.data
  return <>
    {resource.loading && <p role="status">Loading seller return…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A return update is awaiting confirmation. Inspect the saved return or contact support to resolve it before another change.</p>}
    {returned && <>
      <div className="account-card" style={{ overflowWrap: 'anywhere' }}><h2>{returned.order_number}</h2><p>{sellerReturnLabel(returned.status)}</p><p>Return reference: {returned.id}</p><p>Requested {orderDate(returned.requested_at)}</p>{returned.resolved_at && <p>Resolved {orderDate(returned.resolved_at)}</p>}<Link className="text-link" to={`/seller/orders/${returned.seller_order_id}`}>View brand fulfilment</Link></div>
      <section className="account-card"><h3>Customer’s reason</h3><p style={{ whiteSpace: 'pre-wrap' }}>{returned.reason}</p>{returned.notes && <><h3>Saved notes</h3><p style={{ whiteSpace: 'pre-wrap' }}>{returned.notes}</p></>}</section>
      <section className="account-card"><h3>Requested items</h3>{returned.items.map((item) => <article key={item.id}><h4>{item.product_name}</h4><p>{item.variant_label}</p><p>Requested: {item.requested_quantity} of {item.purchased_quantity} purchased · {formatPrice(item.line_subtotal)}</p>{item.reason && <p>{item.reason}</p>}</article>)}</section>
      <section className="account-card"><h3>Refund and dispute status</h3><p>Estimated refund: {formatPrice(returned.estimated_refund_amount)}</p><p>The estimate reflects the requested items and original order discount. Admin handles refund processing and transfer confirmation.</p><p>Refund: {refundLabel(returned.refund_status)}</p><p>Dispute: {disputeLabel(returned.dispute_status)}</p>{returned.status === 'received' && <p>Item receipt is recorded. A completed refund is confirmed separately.</p>}</section>
      {sellerReturnActions(returned).length ? <ReturnActionForm key={JSON.stringify(returned)} value={returned} disabled={disabled} save={(action, body) => save(returned, action, body)} /> : <p>No seller action is currently available for this return.</p>}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh return and discard edits</Button>
  </>
}
const actionLabel = (action: SellerReturnAction) => action === 'approve' ? 'Approve return' : action === 'reject' ? 'Reject return' : 'Mark items received'
function ReturnActionForm({ value, disabled, save }: { value: SellerReturnDetail; disabled: boolean; save: (action: SellerReturnAction, body: { admin_note?: string }) => void }) {
  const actions = sellerReturnActions(value)
  const [action, setAction] = useState<SellerReturnAction>(actions[0]), [note, setNote] = useState(''), [body, setBody] = useState<{ admin_note?: string } | null>(null), [error, setError] = useState<unknown>(null)
  return <section className="account-card"><h3>Update return</h3><form className="auth-form order-request" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { setBody(sellerReturnBody(action, note, value)); setError(null) } catch (reason) { setError(reason) } }}>
    <div className="field"><label htmlFor="seller-return-action">Return action</label><select id="seller-return-action" value={action} disabled={disabled || body !== null} onChange={(e) => setAction(e.target.value as SellerReturnAction)}>{actions.map((option) => <option key={option} value={option}>{actionLabel(option)}</option>)}</select></div>
    <div className="field"><label htmlFor="seller-return-note">Decision note (optional)</label><textarea id="seller-return-note" rows={4} maxLength={500} value={note} disabled={disabled || body !== null} onChange={(e) => setNote(e.target.value)} aria-describedby="seller-return-note-help" /><small id="seller-return-note-help">A new note replaces the saved return notes and may be visible to the customer. Leave blank to keep existing notes.</small></div>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || body !== null}>Review return update</Button>
  </form>{body !== null && <div aria-label="Review return update"><h4>{actionLabel(action)}</h4><p>{action === 'approve' ? 'Approve the request and await the returned items.' : action === 'reject' ? 'Reject this request. The customer may dispute the decision.' : 'Confirm that the returned items have physically arrived. Admin will handle any refund separately.'}</p>{body.admin_note && <p style={{ whiteSpace: 'pre-wrap' }}>New note: {body.admin_note}</p>}<Button disabled={disabled} onClick={() => save(action, body)}>Confirm return update</Button><Button className="button-secondary" disabled={disabled} onClick={() => setBody(null)}>Back to return edits</Button></div>}</section>
}
function refundLabel(status: string | null) { return status === null ? 'No refund recorded' : status === 'pending' ? 'Pending' : status === 'completed' ? 'Completed in platform records' : 'Status unavailable' }
function disputeLabel(status: string | null) { switch (status) { case null: return 'No dispute recorded'; case 'open': return 'Open'; case 'under_review': return 'Under review'; case 'resolved_customer': return 'Resolved for customer'; case 'resolved_seller': return 'Resolved for seller'; case 'closed': return 'Closed'; default: return 'Status unavailable' } }
