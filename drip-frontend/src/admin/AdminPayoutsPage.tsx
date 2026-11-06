import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { payoutLabel, payoutStatuses, type Payout, type WalletPage } from '../seller/wallet'
import { sellerMoney } from './sellers'
import { confirmPayout, payoutActionLabel, payoutActions, payoutBody, payoutMarker, validateAdminPayout, validatePayoutList, type AdminPayout, type PayoutAction } from './payouts'
import './products.css'

export function AdminPayoutsPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Payouts</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to inspect payouts</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Seller funds</p><h1>{detail ? 'Inspect payout' : 'Payouts and transfer records'}</h1><p>Requests have already reserved seller funds. Approval does not debit again. Recording a transfer does not send money.</p>{detail ? isOrderId(id) ? <Inspection key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This payout reference is invalid.</p> : <PayoutList key={user.id} />}</section>
}

function PayoutList() {
  const [params, setParams] = useSearchParams(), status = params.get('status') ?? 'requested', rawPage = params.get('page') ?? '1', page = Number(rawPage)
  const valid = payoutStatuses.includes(status) && /^[1-9]\d*$/.test(rawPage) && Number.isSafeInteger(page)
  return <><div className="field"><label htmlFor="payout-status">Payout status</label><select id="payout-status" value={status} onChange={e => setParams({ status: e.target.value, page: '1' })}>{!payoutStatuses.includes(status) && <option value={status}>Invalid status</option>}{payoutStatuses.map(s => <option key={s} value={s}>{payoutLabel(s)}</option>)}</select></div>{valid ? <Results status={status} page={page} navigate={next => setParams({ status, page: String(next) })} /> : <p role="alert">Choose a valid payout status and positive page number.</p>}</>
}
function Results({ status, page, navigate }: { status: string; page: number; navigate: (page: number) => void }) {
  const validate = useCallback((v: WalletPage<Payout>) => validatePayoutList(v, page, status), [page, status]), resource = useOrderRead(`/admin/wallet/payouts?status=${status}&page=${page}`, true, validate), data = resource.data
  return <>{resource.loading && <p role="status">Loading payouts...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <><p role="status">Page {page} of {data.total_pages} · {data.total} matching payouts</p>{!data.data.length && <EmptyState title="No payouts on this page"><p>Choose another status or page.</p></EmptyState>}{data.data.map(row => <article className="account-card" key={row.id}><h2>{sellerMoney(row.amount)}</h2><p>{payoutLabel(row.status)} · Requested {orderDate(row.requested_at)}</p><p>Destination is shown in the payout inspection only.</p><Link className="text-link" to={`/admin/payouts/${row.id}`}>Inspect payout {row.id}</Link></article>)}</>}<div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous payout page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= data.total_pages} onClick={() => navigate(page + 1)}>Next payout page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh payouts</Button></div></>
}

function Inspection({ owner, id }: { owner: string; id: string }) {
  const path = `/admin/wallet/payouts/${id}`, validate = useCallback((v: AdminPayout) => validateAdminPayout(v, id), [id]), resource = useOrderRead(path, true, validate), value = resource.data
  const write = useAccountWrite(), active = useRef(false), marker = payoutMarker(owner, id)
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(marker) !== null } catch { return true } })
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  function save(before: AdminPayout, action: PayoutAction, body: ReturnType<typeof payoutBody>) {
    if (pending || write.busy || write.blocked) return
    void write.run(async () => {
      let sent = false
      try {
        const current = validate(await request<AdminPayout>(path, { authenticated: true, cache: 'no-store' }))
        if (!active.current) throw new Error('The review session changed. No action was sent.')
        if (JSON.stringify(current) !== JSON.stringify(before)) { resource.retry(); throw new Error('Payout details changed. Inspect the refreshed record.') }
        // Store only an uncertainty marker, never bank details or receipt contents.
        sessionStorage.setItem(marker, 'pending'); setPending(true); sent = true
        const receipt = await request<Payout>(`${path}/${action}`, { authenticated: true, method: 'POST', body: JSON.stringify(body) })
        // A successful HTTP status alone is not proof that the expected record was saved.
        try {
          confirmPayout(receipt, before, action, body)
          const saved = validate(await request<AdminPayout>(path, { authenticated: true, cache: 'no-store' }))
          confirmPayout(saved, before, action, body)
          if (saved.seller_id !== before.seller_id || saved.last_action_by !== owner || saved.completed_at !== receipt.completed_at) throw new Error('Saved receipt mismatch')
        } catch { throw new Error('Payout outcome could not be confirmed. Inspect saved records before repeating any action or transfer.') }
        sessionStorage.removeItem(marker); setPending(false)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'Payout could not be rechecked. No action was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(marker); setPending(false); resource.retry() }
        throw reason
      }
    }, resource.retry, 'Payout record verified. No transfer was initiated by this site.')
  }
  return <><p><Link className="text-link" to="/admin/payouts">Back to payouts</Link></p>{resource.loading && <p role="status">Loading payout detail...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A payout action is awaiting confirmation. Inspect saved records or contact support before repeating it. Do not send another transfer.</p>}{value && <><section className="account-card"><h2>{sellerMoney(value.amount)}</h2><dl><dt>Status</dt><dd>{payoutLabel(value.status)}</dd><dt>Payout reference</dt><dd>{value.id}</dd><dt>Seller reference</dt><dd>{value.seller_id}</dd><dt>Payment method</dt><dd>{value.payment_method}</dd><dt>Saved destination</dt><dd className="admin-product-copy">{value.payment_detail}</dd><dt>Requested</dt><dd>{orderDate(value.requested_at)}</dd><dt>Last recorded administrator</dt><dd>{value.last_action_by || 'Not recorded'}</dd><dt>Admin note</dt><dd className="admin-product-copy">{value.admin_note || 'Not recorded'}</dd><dt>Transfer reference</dt><dd className="admin-product-copy">{value.transfer_reference || 'Not recorded'}</dd><dt>Transfer recorded at</dt><dd>{value.completed_at ? orderDate(value.completed_at) : 'Not recorded'}</dd></dl><p>The destination is the request-time snapshot, not the seller’s current bank settings. Verify the beneficiary independently. The last administrator is not a complete action history.</p></section>{payoutActions(value).length ? <ActionForm key={JSON.stringify(value)} value={value} disabled={pending || write.busy || write.blocked || resource.loading} save={(a, b) => save(value, a, b)} /> : <p role="status">No payout actions are available for this saved record.</p>}</>}<Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh payout and discard draft</Button></>
}
function ActionForm({ value, disabled, save }: { value: AdminPayout; disabled: boolean; save: (action: PayoutAction, body: ReturnType<typeof payoutBody>) => void }) {
  const actions = payoutActions(value), [action, setAction] = useState(actions[0]), [note, setNote] = useState(''), [reference, setReference] = useState(''), [checked, setChecked] = useState(false), [review, setReview] = useState<ReturnType<typeof payoutBody> | null>(null), [error, setError] = useState<unknown>(null), panel = useRef<HTMLDivElement>(null)
  useEffect(() => { if (review) panel.current?.focus() }, [review])
  return <form className="account-card auth-form" onSubmit={e => { e.preventDefault(); if (disabled || review) return; try { setReview(payoutBody(value, action, note, reference, checked)); setError(null) } catch (reason) { setError(reason) } }}><h2>Review payout action</h2><div className="field"><label htmlFor="payout-action">Action</label><select id="payout-action" value={action} disabled={disabled || !!review} onChange={e => { setAction(e.target.value as PayoutAction); setChecked(false); setError(null) }}>{actions.map(a => <option key={a} value={a}>{payoutActionLabel(a)}</option>)}</select></div><p>{action === 'approve' ? 'Approval authorizes the reserved payout; it does not send money or debit the wallet again.' : action === 'reject' ? 'Rejection restores the reserved amount to the seller wallet. Do not reject money already transferred.' : 'Record only a transfer already completed outside this site. Check the exact amount, beneficiary and actual receipt independently. A reference is not provider verification.'}</p><Field label={action === 'reject' ? 'Rejection note' : 'Admin note (optional)'} value={note} maxLength={500} disabled={disabled || !!review} onChange={e => setNote(e.target.value)} />{action === 'complete' && <Field label="Transfer receipt reference" value={reference} maxLength={255} disabled={disabled || !!review} onChange={e => setReference(e.target.value)} />}<label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={e => setChecked(e.target.checked)} />{action === 'complete' ? ' I verified the exact amount was already transferred to the correct beneficiary and checked the receipt.' : ' I checked the amount and saved destination, and verified no transfer has already been made.'}</label>{Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review selected action</Button>{review && <div ref={panel} tabIndex={-1} className="admin-product-confirm"><h3>{payoutActionLabel(action)}?</h3><p>{sellerMoney(value.amount)} · {value.payment_detail}</p><p>{review.admin_note || 'Existing note will be preserved.'}</p>{review.reference && <p>Receipt: {review.reference}</p>}<div className="option-row"><Button disabled={disabled} onClick={() => save(action, review)}>Confirm payout action</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to payout draft</Button></div></div>}</form>
}
