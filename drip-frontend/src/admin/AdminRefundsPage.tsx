import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { paymentMethodLabel } from './orders'
import { paymentStatusLabel } from './payments'
import { sellerMoney } from './sellers'
import { refundConfirmPayload, refundMarker, refundQuery, refundReceipt, refundRequestPayload, validateRefundDetail, validateRefundHistory, validateRefunds, type RefundAccounting, type RefundDetail, type RefundHistory, type RefundReceipt, type RefundRow, type Refunds } from './refunds'
import './products.css'

export function AdminRefundsPage({ mode = 'list' }: { mode?: 'list' | 'detail' | 'payment' }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Refunds</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to inspect refunds</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Refund operations</p><h1>{mode === 'list' ? 'Refund requests and transfers' : mode === 'payment' ? 'Payment refund history' : 'Inspect refund and transfer'}</h1><p>A request reserves refundable balance only. Transfer confirmation records money already sent outside this site; it does not initiate a bank or PayFast transfer.</p>
    {mode === 'list' ? <RefundFilters key={user.id} /> : !isOrderId(id) ? <p role="alert">This refund or payment reference is invalid.</p> : mode === 'payment' ? <PaymentRefunds key={`${user.id}:${id}`} owner={user.id} id={id} /> : <RefundInspection key={`${user.id}:${id}`} owner={user.id} id={id} />}
  </section>
}
function Money({ currency, amount }: { currency: string; amount: string }) { return <>{currency === 'PKR' ? sellerMoney(amount) : `${currency} ${amount}`}</> }
function RefundCard({ row, link = false }: { row: RefundRow; link?: boolean }) {
  return <section className="account-card"><h2>{row.order_number}</h2><dl><dt>Refund status</dt><dd>{row.status === 'pending' ? 'Awaiting recorded transfer' : 'Transfer recorded'}</dd><dt>Refund amount</dt><dd><Money currency={row.currency} amount={row.amount} /></dd><dt>Reason</dt><dd className="admin-product-copy">{row.reason || 'Not recorded'}</dd><dt>Requested</dt><dd>{orderDate(row.requested_at)}</dd><dt>Requested by</dt><dd>{row.requested_by || 'Not recorded'}</dd><dt>Transfer recorded at</dt><dd>{row.processed_at || 'Not recorded'}</dd><dt>Confirmed by</dt><dd>{row.confirmed_by || 'Not recorded'}</dd><dt>Transfer reference</dt><dd className="admin-product-copy">{row.transfer_reference || 'Not recorded'}</dd><dt>Linked return</dt><dd>{row.return_id || 'Direct payment refund; no stock credit'}</dd><dt>Refund reference</dt><dd>{row.refund_id}</dd></dl>{link && <Link className="text-link" to={`/admin/refunds/${row.refund_id}`}>Inspect refund {row.refund_id}</Link>}</section>
}
function RefundFilters() {
  const [params, setParams] = useSearchParams(), status = params.get('status') ?? 'pending', payment = params.get('payment_id') ?? '', page = params.get('page') ?? '1'
  const [draft, setDraft] = useState({ status, payment }), [formError, setFormError] = useState<unknown>(null)
  useEffect(() => { setDraft({ status, payment }); setFormError(null) }, [status, payment])
  let query = '', error: unknown = null
  try { query = refundQuery(status, payment, page) } catch (reason) { error = reason }
  return <><form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); try { setParams(refundQuery(draft.status, draft.payment, '1')); setFormError(null) } catch (reason) { setFormError(reason) } }}>
    <div className="field"><label htmlFor="refund-status">Refund status</label><select id="refund-status" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="all">All refund statuses</option><option value="pending">Awaiting recorded transfer</option><option value="completed">Transfer recorded</option></select></div>
    <Field label="Payment reference (optional)" value={draft.payment} maxLength={36} onChange={(event) => setDraft({ ...draft, payment: event.target.value })} />{Boolean(formError) && <ErrorNotice error={formError} />}<Button type="submit">Apply refund filters</Button>
  </form>{error ? <ErrorNotice error={error} /> : <RefundResults query={query} page={Number(page)} status={status} payment={payment} navigate={(next) => setParams(refundQuery(status, payment, String(next)))} />}</>
}
function RefundResults({ query, page, status, payment, navigate }: { query: string; page: number; status: string; payment: string; navigate: (next: number) => void }) {
  const validate = useCallback((value: Refunds) => validateRefunds(value, page, status, payment), [page, status, payment]), resource = useOrderRead(`/payments/refunds?${query}`, true, validate), data = resource.data
  return <>{resource.loading && <p role="status">Loading refunds...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <><p role="status">Page {page} of {data.total_pages} · {data.total} matching refunds</p><p>Amounts are refund records, not a net revenue or cash-balance total.</p>{!data.data.length && <EmptyState title="No refunds on this page"><p>Change filters or return to the previous page.</p></EmptyState>}{data.data.map((row) => <RefundCard key={row.refund_id} row={row} link />)}</>}
    <div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous refund page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= data.total_pages} onClick={() => navigate(page + 1)}>Next refund page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh refunds</Button></div></>
}
/** Keep ambiguous financial writes locked; never persist a reason, amount or receipt. */
function useRefundAction(owner: string, kind: 'request' | 'confirm', id: string) {
  const write = useAccountWrite(), active = useRef(false), marker = refundMarker(owner, kind, id)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(marker) !== null } catch { return true } })
  function run<T>(check: () => Promise<void>, post: () => Promise<T>, confirm: (value: T) => Promise<void>, refresh: () => void, message: string) {
    if (pending || write.busy || write.blocked) return
    void write.run(async () => {
      let sent = false, value: T
      try {
        await check(); if (!active.current) throw new Error('The review session changed. No action was sent.')
        sessionStorage.setItem(marker, 'pending'); setPending(true); sent = true; value = await post()
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The refund could not be rechecked. No action was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(marker); setPending(false) }
        throw reason
      }
      try { await confirm(value) } catch { throw new Error('The refund outcome could not be confirmed. Inspect saved records before another action.') }
      sessionStorage.removeItem(marker); setPending(false)
    }, refresh, message)
  }
  return { write, pending, run, disabled: pending || write.busy || write.blocked }
}
function PendingNotice({ pending }: { pending: boolean }) { return pending && <p role="alert">A refund action is awaiting confirmation. Inspect the saved records or contact support before repeating it.</p> }
function PaymentRefunds({ owner, id }: { owner: string; id: string }) {
  const path = `/payments/${id}/refunds`, validate = useCallback((v: RefundHistory) => validateRefundHistory(v, id), [id]), resource = useOrderRead(path, true, validate), value = resource.data, action = useRefundAction(owner, 'request', id)
  function save(before: RefundHistory, payload: ReturnType<typeof refundRequestPayload>) {
    action.run(async () => { const current = validate(await request<RefundHistory>(path, { authenticated: true, cache: 'no-store' })); if (JSON.stringify(before) !== JSON.stringify(current)) { resource.retry(); throw new Error('Refund history or balance changed. Inspect the refreshed payment.') } },
      async () => refundReceipt(await request<RefundReceipt>(`/payments/${id}/refund`, { authenticated: true, method: 'POST', body: JSON.stringify(payload) }), id, payload.amount, payload.reason, 'pending'),
      async (receipt) => { const current = validate(await request<RefundHistory>(path, { authenticated: true, cache: 'no-store' })), row = current.refunds.find((item) => item.refund_id === receipt.refund_id); if (!row || row.status !== 'pending' || row.amount !== receipt.amount || row.reason !== payload.reason || row.requested_by !== owner || row.requested_at !== receipt.created_at || row.return_id !== null || row.transfer_reference !== null) throw new Error('Request readback did not match') }, resource.retry, 'Refund request recorded as pending. No transfer or stock credit was made.')
  }
  return <><p><Link className="text-link" to={`/admin/payments/${id}`}>Back to payment inspection</Link></p><p><Link className="text-link" to="/admin/refunds">All refund requests</Link></p>{resource.loading && <p role="status">Loading payment refund history...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={action.write} /><PendingNotice pending={action.pending && !action.write.busy} />{value && <>
    <section className="account-card"><h2>{value.order_number}</h2><p>{paymentMethodLabel(value.payment_method)} · {paymentStatusLabel(value.payment_status)}</p><dl><dt>Saved payment amount</dt><dd><Money currency={value.currency} amount={value.payment_amount} /></dd><dt>Pending requests</dt><dd><Money currency={value.currency} amount={value.pending_refund_amount} /></dd><dt>Recorded transfers</dt><dd><Money currency={value.currency} amount={value.completed_refund_amount} /></dd><dt>Total reserved for refunds</dt><dd><Money currency={value.currency} amount={value.reserved_refund_amount} /></dd><dt>Remaining refundable</dt><dd><Money currency={value.currency} amount={value.remaining_refundable_amount} /></dd></dl><p>Pending requests reserve balance. They do not prove a customer has been paid.</p></section>
    {value.can_request_refund ? <RequestForm key={`${value.reserved_refund_amount}:${value.payment_status}`} value={value} disabled={action.disabled || resource.loading} save={(payload) => save(value, payload)} /> : <p role="status">A new request is unavailable: the payment must be completed in PKR with remaining refundable balance.</p>}
    <section><h2>Saved refund history</h2>{!value.refunds.length && <EmptyState title="No refund requests"><p>No refunds are recorded for this payment.</p></EmptyState>}{value.refunds.map((row) => <RefundCard key={row.refund_id} row={row} link />)}</section>
  </>}<Button className="button-secondary" disabled={resource.loading || action.write.busy} onClick={resource.retry}>Refresh refund history and discard draft</Button></>
}
function RequestForm({ value, disabled, save }: { value: RefundHistory; disabled: boolean; save: (payload: ReturnType<typeof refundRequestPayload>) => void }) {
  const [amount, setAmount] = useState(''), [reason, setReason] = useState(''), [checked, setChecked] = useState(false), [review, setReview] = useState<ReturnType<typeof refundRequestPayload> | null>(null), [error, setError] = useState<unknown>(null), [key] = useState(() => crypto.randomUUID())
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled || review) return; try { setReview(refundRequestPayload(value, amount, reason, checked, key)); setError(null) } catch (e) { setError(e) } }}><h2>Request a direct payment refund</h2><p>For a product return, use its return-linked refund. Do not duplicate it with a direct request here. This request does not return items to stock.</p>
    <Field label="Refund amount (PKR)" inputMode="decimal" value={amount} maxLength={15} disabled={disabled || !!review} onChange={(event) => setAmount(event.target.value)} hint="Use exact rupees with at most two decimal places, within the remaining balance." /><Field label="Refund reason" value={reason} maxLength={500} disabled={disabled || !!review} onChange={(event) => setReason(event.target.value)} hint="5–500 characters. Do not include account secrets." />
    <label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={(event) => setChecked(event.target.checked)} /> I checked existing requests and understand this creates a pending direct refund only, with no transfer or stock credit.</label>{Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review refund request</Button>
    {review && <div className="admin-product-confirm"><h3>Create pending refund request?</h3><p>{value.order_number} · <Money currency="PKR" amount={review.amount} /></p><p>{review.reason}</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm pending refund request</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to refund request draft</Button></div></div>}
  </form>
}
function RefundInspection({ owner, id }: { owner: string; id: string }) {
  const path = `/payments/refunds/${id}`, validate = useCallback((v: RefundDetail) => validateRefundDetail(v, id), [id]), resource = useOrderRead(path, true, validate), value = resource.data, action = useRefundAction(owner, 'confirm', id)
  function save(before: RefundDetail, payload: ReturnType<typeof refundConfirmPayload>) {
    action.run(async () => { const current = validate(await request<RefundDetail>(path, { authenticated: true, cache: 'no-store' })); if (JSON.stringify(before) !== JSON.stringify(current)) { resource.retry(); throw new Error('Refund details or eligibility changed. Inspect the refreshed records.') } },
      async () => refundReceipt(await request<RefundReceipt>(`${path}/confirm`, { authenticated: true, method: 'POST', body: JSON.stringify(payload) }), before.payment_id, before.amount, before.reason, 'completed', id, payload.reference),
      async (receipt) => { const current = validate(await request<RefundDetail>(path, { authenticated: true, cache: 'no-store' })); if (current.status !== 'completed' || current.payment_id !== before.payment_id || current.return_id !== before.return_id || current.amount !== receipt.amount || current.reason !== before.reason || current.requested_by !== before.requested_by || current.requested_at !== before.requested_at || current.transfer_reference !== payload.reference || current.confirmed_by !== owner || current.processed_at !== receipt.processed_at) throw new Error('Transfer readback did not match') }, resource.retry, 'Manual refund transfer recorded and saved evidence confirmed. No transfer was initiated by this site.')
  }
  return <><p><Link className="text-link" to="/admin/refunds">Back to refunds</Link></p>{resource.loading && <p role="status">Loading refund detail...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={action.write} /><PendingNotice pending={action.pending && !action.write.busy} />{value && <><RefundCard row={value} /><p><Link className="text-link" to={`/admin/payments/${value.payment_id}/refunds`}>Inspect payment refund history</Link></p><p><Link className="text-link" to={`/admin/orders/${value.order_id}`}>Inspect full saved order</Link></p>
    <section className="account-card"><h2>Recorded workflow history</h2>{value.history.map((event) => <p key={event.event}>{event.event === 'requested' ? 'Request created' : 'Transfer recorded'} · {event.occurred_at} · Administrator: {event.actor_id || 'Not recorded'}{event.transfer_reference && <> · Reference: {event.transfer_reference}</>}</p>)}<p>Linked return status: {value.linked_return_status || 'No linked return'}</p>{value.confirmation_blockers.map((message) => <p role="status" key={message}>{message}</p>)}</section>
    <Accounting value={value.accounting} currency={value.currency} />{value.can_confirm_refund && <ConfirmForm key={`${value.refund_id}:${value.return_id}:${value.amount}`} value={value} disabled={action.disabled || resource.loading} save={(payload) => save(value, payload)} />}
  </>}<Button className="button-secondary" disabled={resource.loading || action.write.busy} onClick={resource.retry}>Refresh refund and discard transfer draft</Button></>
}
const accountingLabels = { merchandise_amount: 'Merchandise allocation', shipping_amount: 'Shipping allocation', commission_reversal_amount: 'Commission reversal', seller_reversal_amount: 'Seller entitlement reversal', recovered_amount: 'Recovered from seller balances', settlement_offset_amount: 'Offset against settlement', platform_shortfall_amount: 'Platform-covered seller shortfall', platform_funded_amount: 'Total platform-funded portion' } as const
function Accounting({ value, currency }: { value: RefundAccounting | null; currency: string }) {
  return <section className="account-card"><h2>Seller and platform reconciliation</h2>{!value ? <p>No accounting allocation is recorded yet. This does not establish reconciliation.</p> : <><p>{value.reconciled ? 'Accounting allocations reconciled' : 'Accounting allocations still awaiting reconciliation'}</p><dl>{Object.entries(accountingLabels).map(([key, label]) => <Fragment key={key}><dt>{label}</dt><dd><Money currency={currency} amount={value[key as keyof typeof accountingLabels]} /></dd></Fragment>)}</dl><p>Recovered funds, settlement offsets and platform shortfalls are different accounting outcomes, not bank-transfer receipts or seller payouts.</p>{value.allocations.map((row) => <article className="admin-product-variant" key={row.seller_order_id}><h3>Seller {row.seller_id}</h3><p>Fulfilment reference: {row.seller_order_id}</p><p>{row.reconciled ? 'Allocation reconciled' : 'Allocation pending settlement/reconciliation'}</p><p>Recorded commission rate: {row.commission_rate ?? 'Not yet applied'}</p>{(['merchandise_amount', 'commission_reversal_amount', 'seller_reversal_amount', 'recovered_amount', 'settlement_offset_amount', 'platform_shortfall_amount'] as const).map((key) => <p key={key}>{accountingLabels[key]}: <Money currency={currency} amount={row[key]} /></p>)}</article>)}</>}</section>
}
function ConfirmForm({ value, disabled, save }: { value: RefundDetail; disabled: boolean; save: (payload: ReturnType<typeof refundConfirmPayload>) => void }) {
  const [reference, setReference] = useState(''), [checked, setChecked] = useState(false), [review, setReview] = useState<ReturnType<typeof refundConfirmPayload> | null>(null), [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled || review) return; try { setReview(refundConfirmPayload(value, reference, checked)); setError(null) } catch (e) { setError(e) } }}><h2>Record an already-completed manual transfer</h2><p>Check the beneficiary, exact amount and actual receipt independently. A reference is not provider verification. Do not repeat a transfer just because recording its result failed.</p><p>Amount: <Money currency={value.currency} amount={value.amount} />. {value.return_id ? 'Confirmation also reconciles this received return and its stock credit.' : 'This direct refund does not credit inventory.'}</p>
    <Field label="Refund transfer receipt reference" value={reference} maxLength={255} disabled={disabled || !!review} onChange={(event) => setReference(event.target.value)} hint="3–255 characters from the completed transfer. Do not enter account secrets." /><label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={(event) => setChecked(event.target.checked)} /> I verified that the exact refund amount was already sent to the correct beneficiary and checked the receipt. This records the result; it does not initiate payment.</label>{Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review transfer confirmation</Button>
    {review && <div className="admin-product-confirm"><h3>Record the completed refund transfer?</h3><p>{value.order_number} · <Money currency={value.currency} amount={value.amount} /></p><p>Receipt: {review.reference}</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm recorded refund transfer</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to transfer draft</Button></div></div>}
  </form>
}
