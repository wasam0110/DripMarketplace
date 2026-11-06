import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, statusLabel, useOrderRead } from '../orders/api'
import { paymentMethodLabel } from './orders'
import { sellerMoney } from './sellers'
import { collectionMarker, collectionPayload, confirmCollection, confirmCollectionReadback, paymentQuery, paymentStatusLabel, paymentStatuses, samePaymentReview, validatePayment, validatePayments, type AdminPayment, type AdminPayments, type CollectionReceipt, type PaymentRow } from './payments'
import './products.css'

export function AdminPaymentsPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Payments</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to inspect payments</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Payment operations</p><h1>{detail ? 'Inspect payment and collection' : 'Payments and COD collection'}</h1><p>Record cash collection only after checking the actual receipt. COD order approval is separate. This screen does not transfer money, issue refunds or pay out sellers.</p>
    {detail ? isOrderId(id) ? <PaymentInspection key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This payment reference is invalid.</p> : <PaymentFilters key={user.id} />}
  </section>
}
function PaymentCard({ row }: { row: PaymentRow }) {
  return <section className="account-card"><h2>{row.order_number}</h2><dl><dt>Payment method</dt><dd>{paymentMethodLabel(row.method)}</dd><dt>Payment status</dt><dd>{paymentStatusLabel(row.status)}</dd><dt>Saved payment amount</dt><dd>{row.currency === 'PKR' ? sellerMoney(row.amount) : `${row.currency} ${row.amount}`}</dd><dt>Payment created</dt><dd>{orderDate(row.created_at)}</dd><dt>Collection/payment date</dt><dd>{row.paid_at ? row.paid_at : 'Not recorded'}</dd><dt>Saved reference</dt><dd className="admin-product-copy">{row.gateway_reference || 'Not recorded'}</dd><dt>Payment reference</dt><dd>{row.id}</dd></dl></section>
}
function PaymentFilters() {
  const [params, setParams] = useSearchParams(), status = params.get('status') ?? 'pending', method = params.get('method') ?? 'cod', page = params.get('page') ?? '1'
  const [draft, setDraft] = useState({ status, method }), [formError, setFormError] = useState<unknown>(null)
  useEffect(() => { setDraft({ status, method }); setFormError(null) }, [status, method])
  let query = '', error: unknown = null
  try { query = paymentQuery(status, method, page) } catch (reason) { error = reason }
  return <><form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); try { setParams(paymentQuery(draft.status, draft.method, '1')); setFormError(null) } catch (reason) { setFormError(reason) } }}>
    <div className="field"><label htmlFor="payment-status">Payment status</label><select id="payment-status" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="all">All payment statuses</option>{paymentStatuses.map((v) => <option key={v} value={v}>{paymentStatusLabel(v)}</option>)}</select></div>
    <div className="field"><label htmlFor="payment-method">Payment method</label><select id="payment-method" value={draft.method} onChange={(event) => setDraft({ ...draft, method: event.target.value })}><option value="all">All payment methods</option><option value="cod">Cash on delivery</option><option value="payfast">PayFast</option></select></div>
    <p>All methods includes historical records. A pending COD payment is not necessarily delivered or eligible for collection.</p>{Boolean(formError) && <ErrorNotice error={formError} />}<Button type="submit">Apply payment filters</Button>
  </form>{error ? <ErrorNotice error={error} /> : <PaymentResults query={query} page={Number(page)} status={status} method={method} navigate={(next) => setParams(paymentQuery(status, method, String(next)))} />}</>
}
function PaymentResults({ query, page, status, method, navigate }: { query: string; page: number; status: string; method: string; navigate: (next: number) => void }) {
  const validate = useCallback((value: AdminPayments) => validatePayments(value, page, status, method), [page, status, method])
  const resource = useOrderRead(`/payments?${query}`, true, validate), data = resource.data
  return <>{resource.loading && <p role="status">Loading payments...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <><p role="status">Page {page} of {data.total_pages} · {data.total} matching payments</p><p>Amounts are saved payment records, not a revenue total or proof of cash received.</p>{!data.data.length && <EmptyState title="No payments on this page"><p>Change filters or return to the previous page.</p></EmptyState>}{data.data.map((row) => <article key={row.id}><PaymentCard row={row} /><p><Link className="text-link" to={`/admin/payments/${row.id}`}>Inspect payment {row.order_number}</Link></p></article>)}</>}
    <div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous payment page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= data.total_pages} onClick={() => navigate(page + 1)}>Next payment page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh payments</Button></div></>
}
function PaymentInspection({ owner, id }: { owner: string; id: string }) {
  const path = `/payments/${id}`, validate = useCallback((value: AdminPayment) => validatePayment(value, id), [id])
  const resource = useOrderRead(path, true, validate), payment = resource.data, write = useAccountWrite(), active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(collectionMarker(owner, id)) !== null } catch { return true } })
  function save(before: AdminPayment, payload: ReturnType<typeof collectionPayload>) {
    if (resource.loading || write.busy || write.blocked || pending) return
    void write.run(async () => {
      let sent = false, receipt: CollectionReceipt
      try {
        const current = validate(await request<AdminPayment>(path, { authenticated: true, cache: 'no-store' }))
        if (!active.current) throw new Error('The review session changed. No collection was sent.')
        if (!samePaymentReview(before, current)) { resource.retry(); throw new Error('Payment or order changed. Inspect the refreshed records before collecting.') }
        sessionStorage.setItem(collectionMarker(owner, id), 'pending'); setPending(true); sent = true
        receipt = confirmCollection(await request<CollectionReceipt>(`${path}/cod-collection`, { authenticated: true, method: 'POST', body: JSON.stringify(payload) }), before, payload.reference, owner)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'Collection could not be rechecked. No action was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(collectionMarker(owner, id)); setPending(false) }
        throw reason
      }
      try { confirmCollectionReadback(await request<AdminPayment>(path, { authenticated: true, cache: 'no-store' }), before, receipt) }
      catch { throw new Error('Collection could not be confirmed. Inspect saved evidence before repeating the action.') }
      sessionStorage.removeItem(collectionMarker(owner, id)); setPending(false)
    }, resource.retry, 'COD collection recorded and saved payment evidence confirmed. No seller payout was made.')
  }
  return <><p><Link className="text-link" to="/admin/payments">Back to payments</Link></p>{resource.loading && <p role="status">Loading payment detail...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A collection is awaiting confirmation. Inspect the saved reference or contact support before another action.</p>}{payment && <>
    <PaymentCard row={payment} /><p><Link className="text-link" to={`/admin/payments/${payment.id}/refunds`}>Inspect refund history or request a refund</Link></p><section className="account-card"><h2>Collection eligibility and evidence</h2><dl><dt>Currency</dt><dd>{payment.currency}</dd><dt>Order status</dt><dd>{statusLabel(payment.order_status)}</dd><dt>Recorded by administrator</dt><dd>{payment.collection_recorded_by || 'Not recorded (may be a historical payment)'}</dd></dl><p><Link className="text-link" to={`/admin/orders/${payment.order_id}`}>Inspect full saved order {payment.order_number}</Link></p>{payment.collection_blockers.map((v) => <p role="status" key={v}>{v}</p>)}<p>A manual reference records the administrator's confirmation; it is not independent provider verification. Seller proceeds follow the existing settlement and hold policy, not an immediate payout.</p></section>
    {payment.can_record_cod_collection && <CollectionForm key={`${payment.order_updated_at}:${payment.amount}`} payment={payment} disabled={resource.loading || write.busy || write.blocked || pending} save={(payload) => save(payment, payload)} />}
  </>}<Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh payment and discard collection draft</Button></>
}
function CollectionForm({ payment, disabled, save }: { payment: AdminPayment; disabled: boolean; save: (payload: ReturnType<typeof collectionPayload>) => void }) {
  const [reference, setReference] = useState(''), [checked, setChecked] = useState(false), [review, setReview] = useState<ReturnType<typeof collectionPayload> | null>(null), [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled || review) return; try { setReview(collectionPayload(payment, reference, checked)); setError(null) } catch (reason) { setError(reason) } }}>
    <h2>Record COD cash collection</h2><p>Full saved amount: {sellerMoney(payment.amount)}. Partial collections are not supported here.</p>
    <Field label="Collection receipt reference" value={reference} maxLength={255} disabled={disabled || !!review} onChange={(event) => setReference(event.target.value)} hint="3–255 characters from the actual receipt or courier reconciliation record. Do not enter secrets." />
    <label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={(event) => setChecked(event.target.checked)} /> I checked the delivery and receipt and confirm the full saved amount was actually received. This records collection and settlement, not a seller payout.</label>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review cash collection</Button>
    {review && <div className="admin-product-confirm"><h3>Confirm cash already received?</h3><p>{payment.order_number} · {sellerMoney(payment.amount)}</p><p>Receipt reference: {review.reference}</p><p>Payment: {payment.id}</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm cash collection</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to collection draft</Button></div></div>}
  </form>
}
