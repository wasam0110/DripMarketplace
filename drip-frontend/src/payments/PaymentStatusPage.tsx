import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { paymentStatusText, validatePaymentStatus, type PaymentStatus } from './status'

export function PaymentStatusPage() {
  const { id = '' } = useParams()
  const auth = useAuth()
  useEffect(() => {
    // Redirect hints and provider query fields are never payment evidence or credentials.
    window.history.replaceState(window.history.state, '', window.location.pathname)
  }, [id])
  if (!isOrderId(id)) return <section className="container page"><h1>Payment reference unavailable</h1><Link to="/orders">Your orders</Link></section>
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  return <PaymentLookup key={`${auth.user?.id ?? 'guest'}:${id}`} id={id} signedIn={Boolean(auth.user && !auth.error)} />
}
function PaymentLookup({ id, signedIn }: { id: string; signedIn: boolean }) {
  const [guest, setGuest] = useState(!signedIn)
  const [draft, setDraft] = useState('')
  const [token, setToken] = useState('')
  const [error, setError] = useState<unknown>(null)
  function submit(event: FormEvent) {
    event.preventDefault()
    const value = draft.trim()
    if (!value || /\s/.test(value)) { setError(new Error('Enter the complete private guest access code.')); return }
    setToken(value); setDraft(''); setError(null)
  }
  return <section className="container page"><p className="eyebrow">Your payment</p><h1>Check payment status</h1>
    <p>A success or failure redirect does not confirm payment. Only the protected backend status below is authoritative.</p>
    <p>Order reference: {id}</p>
    {(!guest || token) ? <PaymentPanel key={`${guest}:${token}`} id={id} authenticated={!guest} token={guest ? token : undefined} />
      : <form className="account-card auth-form" onSubmit={submit}>
        <p>For a guest order, enter its private access code again after returning from the payment provider. Your order reference alone is not enough.</p>
        <Field label="Private guest access code" type="password" autoComplete="off" required maxLength={4096} value={draft} onChange={(event) => setDraft(event.target.value)} />
        <p className="muted">The code stays in memory and is sent only in a request header. Leaving or reloading this page clears it.</p>
        {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit">Check guest payment</Button>
      </form>}
    {guest && token && <Button className="button-secondary" onClick={() => { setToken(''); setDraft('') }}>Clear guest access</Button>}
    {signedIn ? <p><Button className="button-secondary" onClick={() => { setGuest(!guest); setToken(''); setDraft(''); setError(null) }}>{guest ? 'Use my account access' : 'Use a guest access code'}</Button></p> : <p><Link to="/login">Sign in for an account order</Link></p>}
    <p className="notice">Payment initiation and retries are not available on this screen. Do not create another order to resolve an uncertain payment.</p>
  </section>
}
function PaymentPanel({ id, authenticated, token }: { id: string; authenticated: boolean; token?: string }) {
  const validate = useCallback((value: PaymentStatus) => validatePaymentStatus(value, id), [id])
  const resource = useOrderRead(`/payments/${id}/status`, authenticated, validate, token)
  const payment = resource.data
  const error = resource.error instanceof ApiError && [401, 403, 404].includes(resource.error.status)
    ? new Error('Payment information is unavailable with this access. Check the owning account or private guest code. Do not assume payment failed.') : resource.error
  return <section aria-label="Backend payment status">
    {resource.loading && <p role="status">Loading payment status…</p>}
    {Boolean(error) && <ErrorNotice error={error} />}
    {payment && <article className="account-card"><h2>{paymentStatusText(payment.status).label}</h2><p role="status">{paymentStatusText(payment.status).detail}</p>
      <dl><dt>Payment amount (PKR)</dt><dd>{formatPrice(payment.amount)}</dd><dt>Method</dt><dd>{payment.method === 'payfast' ? 'PayFast' : payment.method === 'cod' ? 'Cash on delivery' : 'Method unavailable'}</dd></dl>
      <p>Payment reference: {payment.payment_id}</p>
      {payment.paid_at && <p>Recorded payment date: {orderDate(payment.paid_at)}</p>}
      <p className="muted">Last loaded backend snapshot. Refresh to check for changes.</p>
    </article>}
    <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh payment status</Button>
    <p><Link to={authenticated ? `/orders/${id}` : '/track'}>{authenticated ? 'View your order' : 'Track a guest order separately'}</Link></p>
  </section>
}
