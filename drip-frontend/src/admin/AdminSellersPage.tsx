import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { confirmSellerDecision, sameSellerReview, sellerDecisionBody, sellerDecisionMarker, sellerDecisions, sellerLabel, sellerLogo, sellerMoney, sellerStatuses, validateAdminSellerDetail, validateAdminSellers, type AdminSellerDetail, type AdminSellerPage, type SellerDecision } from './sellers'
import './sellers.css'
import { canRecordRegistration, confirmRegistrationPayment, registrationPaymentBody, type RegistrationPayment } from './sellers'

export function AdminSellersPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Seller review</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to review sellers</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-sellers"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Platform management</p><h1>{detail ? 'Review seller' : 'Seller applications'}</h1>
    {detail ? isOrderId(id) ? <SellerReview key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This seller reference is invalid.</p> : <SellerList key={user.id} />}
  </section>
}
function SellerList() {
  const [status, setStatus] = useState('pending_approval'), [search, setSearch] = useState(''), [query, setQuery] = useState(''), [page, setPage] = useState(1)
  const check = useCallback((value: AdminSellerPage) => validateAdminSellers(value, page, status), [page, status])
  const params = new URLSearchParams({ status, page: String(page), per_page: '25' }); if (query) params.set('q', query)
  const resource = useOrderRead(`/admin/sellers?${params}`, true, check), result = resource.data
  return <>
    <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); setQuery(search.trim()); setPage(1) }}>
      <div className="field"><label htmlFor="admin-seller-status">Seller status</label><select id="admin-seller-status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="all">All statuses</option>{sellerStatuses.map((value) => <option key={value} value={value}>{sellerLabel(value)}</option>)}</select></div>
      <Field label="Search brand name" value={search} maxLength={100} onChange={(event) => setSearch(event.target.value)} /><Button type="submit">Search sellers</Button>
    </form>
    {resource.loading && <p role="status">Loading sellers…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {result && <>
      <p role="status">Page {result.page} of {result.total_pages} · {result.total} matching sellers</p>
      {!result.data.length && <EmptyState title="No sellers on this page"><p>Change the filters or try a previous page.</p></EmptyState>}
      {result.data.map((row) => <article className="account-card" key={row.id}><h2>{row.brand_name}</h2><p>{sellerLabel(row.status)} · Joined {orderDate(row.joined_at)}</p><dl><dt>Published products</dt><dd>{row.product_count}</dd><dt>Slots used</dt><dd>{row.slots_used} of {row.total_slots}</dd></dl><Link className="text-link" to={`/admin/sellers/${row.id}`}>Review {row.brand_name}</Link></article>)}
    </>}
    <div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Previous seller page</Button><Button className="button-secondary" disabled={resource.loading || !result || page >= result.total_pages} onClick={() => setPage((value) => value + 1)}>Next seller page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh seller list</Button></div>
  </>
}
function SellerReview({ owner, id }: { owner: string; id: string }) {
  const path = `/admin/sellers/${id}`, check = useCallback((value: AdminSellerDetail) => validateAdminSellerDetail(value, id), [id])
  const resource = useOrderRead(path, true, check), write = useAccountWrite()
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(sellerDecisionMarker(owner, id)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || pending || resource.loading || !resource.data
  function save(before: AdminSellerDetail, action: SellerDecision, body: { reason?: string }) {
    if (disabled || !sellerDecisions(before.status).includes(action)) return
    update(before, action, body, (saved) => confirmSellerDecision(saved, before, action, body), 'Seller decision saved and confirmed.')
  }
  function recordPayment(before: AdminSellerDetail, body: RegistrationPayment) {
    if (disabled || !canRecordRegistration(before)) return
    update(before, 'registration-payment', body, (saved) => confirmRegistrationPayment(saved, before, body, owner), 'Registration payment saved and confirmed. Seller approval is separate.')
  }
  function update(before: AdminSellerDetail, action: string, body: object, confirm: (saved: AdminSellerDetail) => AdminSellerDetail, notice: string) {
    void write.run(async () => {
      let sent = false
      try {
        const latest = check(await request<AdminSellerDetail>(path, { authenticated: true, cache: 'no-store' }))
        if (!sameSellerReview(before, latest)) { resource.retry(); throw new Error('The seller status or application details changed. Review the refreshed application before deciding.') }
        sessionStorage.setItem(sellerDecisionMarker(owner, id), 'pending'); setPending(true); sent = true
        await request(`${path}/${action}`, { authenticated: true, method: 'POST', ...(Object.keys(body).length ? { body: JSON.stringify(body) } : {}) })
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The application could not be rechecked. No decision was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(sellerDecisionMarker(owner, id)); setPending(false) }
        throw reason
      }
      let saved: AdminSellerDetail
      try { saved = confirm(await request<AdminSellerDetail>(path, { authenticated: true, cache: 'no-store' })) }
      catch { throw new Error('The seller update could not be confirmed. Inspect the saved seller record before repeating it.') }
      sessionStorage.removeItem(sellerDecisionMarker(owner, id)); setPending(false)
      return saved
    }, resource.retry, notice)
  }
  const value = resource.data
  return <>
    <p><Link className="text-link" to="/admin/sellers">Back to seller applications</Link></p>
    <p><Link className="text-link" to={`/admin/products?seller_id=${id}`}>View this seller’s products</Link></p>
    {resource.loading && <p role="status">Loading seller application…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A seller update is awaiting confirmation. Inspect the saved record or contact support before another change.</p>}
    {value && <>
      <section className="account-card"><h2>{value.brand_name}</h2><p>{sellerLabel(value.status)}</p><p>Seller reference: {value.id}</p><p>Joined {orderDate(value.joined_at)}</p><dl><dt>Brand slug</dt><dd>{value.slug}</dd><dt>Published products</dt><dd>{value.product_count}</dd><dt>Slots used</dt><dd>{value.slots_used} of {value.total_slots}</dd><dt>Quoted registration fee</dt><dd>{sellerMoney(value.registration_fee)}</dd></dl><p>The quoted fee is not a payment receipt. Registration-payment confirmation is separate from approval.</p></section>
      <section className="account-card"><h2>Brand application</h2>{sellerLogo(value.logo_url) && <img className="admin-seller-logo" src={sellerLogo(value.logo_url)!} alt={`${value.brand_name} submitted logo`} referrerPolicy="no-referrer" loading="lazy" />}<dl><dt>Description</dt><dd className="admin-seller-copy">{value.description || 'Not supplied'}</dd><dt>WhatsApp</dt><dd>{value.whatsapp_number || 'Not supplied'}</dd><dt>Instagram</dt><dd>{value.instagram_handle || 'Not supplied'}</dd><dt>Return policy</dt><dd className="admin-seller-copy">{value.return_policy || 'Not supplied'}</dd></dl>{value.rejected_reason && <><h3>Saved review reason</h3><p className="admin-seller-copy">{value.rejected_reason}</p></>}</section>
      <section className="account-card"><h2>Recorded financial context</h2><dl><dt>Delivered shipment value</dt><dd>{sellerMoney(value.total_gmv)}</dd><dt>Commission after reversals</dt><dd>{sellerMoney(value.platform_cut)}</dd><dt>Available wallet balance</dt><dd>{sellerMoney(value.available_balance)}</dd><dt>Pending release</dt><dd>{sellerMoney(value.pending_balance)}</dd></dl><p>These totals use different records and are not a reconciliation statement. A seller decision does not record a payment, refund or payout.</p></section>
      <RegistrationReceipt value={value} />
      {canRecordRegistration(value) && <RegistrationForm key={`registration:${JSON.stringify(value)}`} value={value} disabled={disabled} save={(body) => recordPayment(value, body)} />}
      {sellerDecisions(value.status).length ? <DecisionForm key={`decision:${JSON.stringify(value)}`} value={value} disabled={disabled} save={(action, body) => save(value, action, body)} /> : <p>No review action is available for this seller status.</p>}
      {value.status === 'pending_payment' && <p>Approval is unavailable while registration payment is pending. Verify and record the transfer separately before reviewing approval.</p>}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh seller and discard edits</Button>
  </>
}
function RegistrationReceipt({ value }: { value: AdminSellerDetail }) {
  const partial = value.registration_paid_at === null && (value.registration_payment_reference !== null || value.registration_paid_by !== null)
  return <section className="account-card"><h2>Registration payment record</h2><dl><dt>Amount outstanding</dt><dd>{sellerMoney(value.registration_amount_due)}</dd></dl>
    {value.registration_paid_at ? <><p>Payment recorded {orderDate(value.registration_paid_at)}. This is a platform record of a manually verified transfer, not independent bank confirmation.</p><dl><dt>Recorded amount</dt><dd>{sellerMoney(value.registration_fee)}</dd><dt>Transfer reference</dt><dd>{value.registration_payment_reference || 'Not recorded'}</dd><dt>Recorded by admin</dt><dd>{value.registration_paid_by || 'Not recorded'}</dd></dl>{(!value.registration_payment_reference || !value.registration_paid_by) && <p>Receipt metadata is incomplete. Reconcile the existing record before any correction.</p>}</>
      : partial ? <p>Registration payment metadata is incomplete. Reconcile the saved record before recording another transfer.</p>
        : <p>{Number(value.registration_fee) === 0 ? 'No registration fee was quoted; no paid receipt is recorded.' : 'No registration payment receipt is recorded.'}</p>}
  </section>
}
function RegistrationForm({ value, disabled, save }: { value: AdminSellerDetail; disabled: boolean; save: (body: RegistrationPayment) => void }) {
  const [amount, setAmount] = useState(''), [reference, setReference] = useState(''), [verified, setVerified] = useState(false), [review, setReview] = useState<RegistrationPayment | null>(null), [error, setError] = useState<unknown>(null)
  return <section className="account-card"><h2>Record registration transfer</h2><p>Verify the money reached the receiving account first. This form records that manual check; it does not collect payment or approve this seller.</p><form className="auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled) return; try { if (!verified) throw new Error('Verify the transfer in the receiving account before recording it.'); setReview(registrationPaymentBody(value, amount, reference)); setError(null) } catch (problem) { setError(problem) } }}>
    <Field label="Received registration amount (PKR)" value={amount} inputMode="decimal" maxLength={13} disabled={disabled || review !== null} onChange={(event) => setAmount(event.target.value)} />
    <Field label="Registration transfer reference" value={reference} maxLength={255} disabled={disabled || review !== null} onChange={(event) => setReference(event.target.value)} />
    <label className="admin-payment-verification"><input type="checkbox" checked={verified} disabled={disabled || review !== null} onChange={(event) => setVerified(event.target.checked)} />I verified this transfer in the receiving account</label>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || review !== null}>Review registration payment</Button>
  </form>{review && <div className="admin-decision-review"><h3>Confirm payment record for {value.brand_name}</h3><p>Amount: {sellerMoney(review.amount)}</p><p>Transfer reference: {review.reference}</p><p>The application will await a separate approval decision.</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm registration payment</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to payment edits</Button></div></div>}</section>
}
const decisionLabels: Record<SellerDecision, string> = { approve: 'Approve seller', reject: 'Reject application', suspend: 'Suspend seller', reinstate: 'Reinstate seller' }
const consequences: Record<SellerDecision, string> = {
  approve: 'Activate this brand for selling. This decision does not confirm a registration payment.',
  reject: 'Reject this pending application. The reason may be shared with the seller.',
  suspend: 'Suspend selling access and hide this brand from public shopping. This does not cancel existing orders or settle balances. The reason is saved for review.',
  reinstate: 'Restore this suspended brand to active status. Independently moderated products remain hidden.',
}
function DecisionForm({ value, disabled, save }: { value: AdminSellerDetail; disabled: boolean; save: (action: SellerDecision, body: { reason?: string }) => void }) {
  const [action, setAction] = useState<SellerDecision>(sellerDecisions(value.status)[0]), [reason, setReason] = useState(''), [review, setReview] = useState<{ reason?: string } | null>(null), [error, setError] = useState<unknown>(null)
  return <section className="account-card"><h2>Seller decision</h2><form className="auth-form order-request" onSubmit={(event) => { event.preventDefault(); if (disabled) return; try { setReview(sellerDecisionBody(value.status, action, reason)); setError(null) } catch (problem) { setError(problem) } }}>
    <div className="field"><label htmlFor="admin-seller-decision">Review action</label><select id="admin-seller-decision" value={action} disabled={disabled || review !== null} onChange={(event) => setAction(event.target.value as SellerDecision)}>{sellerDecisions(value.status).map((option) => <option key={option} value={option}>{decisionLabels[option]}</option>)}</select></div>
    {(action === 'reject' || action === 'suspend') && <div className="field"><label htmlFor="admin-seller-reason">Decision reason</label><textarea id="admin-seller-reason" rows={4} maxLength={1000} disabled={disabled || review !== null} value={reason} onChange={(event) => setReason(event.target.value)} aria-describedby="admin-seller-reason-help" /><small id="admin-seller-reason-help">10–1,000 characters. Avoid private payment details; rejection reasons may be sent to the seller.</small></div>}
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || review !== null}>Review seller decision</Button>
  </form>{review !== null && <div className="admin-decision-review" aria-label="Confirm seller decision"><h3>{decisionLabels[action]}: {value.brand_name}</h3><p>{consequences[action]}</p>{review.reason && <p className="admin-seller-copy">Reason: {review.reason}</p>}<div className="option-row"><Button disabled={disabled} onClick={() => save(action, review)}>Confirm seller decision</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to decision edits</Button></div></div>}</section>
}
