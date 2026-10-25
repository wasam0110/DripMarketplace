import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { request } from '../api/client'
import type { OrderResult } from '../checkout/submission'
import { Button, ErrorNotice, Field } from '../components/ui'
import { payfastEnabled, paymentAttemptKey, validateHandoff, type PayFastHandoff as Handoff } from './payfast'

export function PayFastHandoff({ order, account, recovered }: { order: OrderResult; account: boolean; recovered: boolean }) {
  const [attempted, setAttempted] = useState(() => {
    try { return sessionStorage.getItem(paymentAttemptKey(order.order_id)) !== null } catch { return true }
  })
  const [handoff, setHandoff] = useState<Handoff | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [saved, setSaved] = useState(false)
  const [showCode, setShowCode] = useState(false)
  const [sent, setSent] = useState(false)
  const lock = useRef(false)
  const sentLock = useRef(false)
  const active = useRef(false)
  const form = useRef<HTMLFormElement>(null)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  async function prepare() {
    if (lock.current || attempted || recovered || !payfastEnabled || order.status !== 'pending_payment' || (!account && (!order.guest_token || !saved))) return
    lock.current = true; setBusy(true); setError(null); setAttempted(true)
    try {
      // A non-secret tab marker survives reload; never persist provider tokens or private guest codes.
      sessionStorage.setItem(paymentAttemptKey(order.order_id), 'started')
      if (sessionStorage.getItem(paymentAttemptKey(order.order_id)) !== 'started') throw new Error('Tab storage is unavailable. Payment initiation was not sent.')
      const result = await request<Handoff>('/payments/initiate', { method: 'POST', authenticated: account,
        headers: !account && order.guest_token ? { 'X-Guest-Token': order.guest_token } : undefined,
        body: JSON.stringify({ order_id: order.order_id }),
      })
      const validated = validateHandoff(result, order, window.location.origin, import.meta.env.VITE_PAYFAST_CALLBACK_ORIGIN || window.location.origin)
      if (active.current) setHandoff(validated)
    } catch (reason) { if (active.current) setError(reason) }
    finally { if (active.current) setBusy(false) }
  }
  function send() {
    if (!handoff || sentLock.current || !form.current || !payfastEnabled) return
    try {
      validateHandoff(handoff, order, window.location.origin, import.meta.env.VITE_PAYFAST_CALLBACK_ORIGIN || window.location.origin)
      setSent(true)
      sentLock.current = true
      // Native same-tab POST; no card details are collected by WearHowZ.
      HTMLFormElement.prototype.submit.call(form.current)
    } catch (reason) { setHandoff(null); setError(reason) }
  }
  return <section aria-label="PayFast handoff"><h2>Payment is a separate step</h2>
    <p>Your order exists, but this screen does not confirm payment. Do not create another order to resolve a payment problem.</p>
    {!account && order.guest_token && <><Field label="Private guest access code for this order" type={showCode ? 'text' : 'password'} readOnly value={order.guest_token} autoComplete="off" />
      <label className="checkbox-label"><input type="checkbox" checked={showCode} onChange={(event) => setShowCode(event.target.checked)} />Show private access code</label>
      <label className="checkbox-label"><input type="checkbox" checked={saved} onChange={(event) => setSaved(event.target.checked)} />I have saved this private code securely for the return screen.</label></>}
    {Boolean(error) && <ErrorNotice error={error} />}
    {!payfastEnabled ? <p>Online payment handoff is disabled in this build.</p>
      : handoff ? <><p>Continue to the payment provider only once. This form contains a short-lived provider token and is not stored by this app.</p>
        <form ref={form} action={handoff.checkout_url} method="post" onSubmit={(event) => event.preventDefault()}>
          {Object.entries(handoff.payfast_payload).map(([name, value]) => <input key={name} type="hidden" name={name} value={value} />)}
        </form><Button disabled={sent} onClick={send}>{sent ? 'Handoff sent — check payment status on return' : 'Continue to PayFast'}</Button></>
      : attempted || recovered || order.status !== 'pending_payment' ? <p role="status">A new payment attempt is locked on this screen. Check backend status before any further action; contact support if the outcome is unresolved.</p>
        : <Button disabled={busy || (!account && (!order.guest_token || !saved))} onClick={() => void prepare()}>Prepare PayFast payment</Button>}
    {busy && <p role="status">Preparing the provider handoff…</p>}
    <p><Link to={`/payments/${order.order_id}`}>Check backend payment status</Link></p>
  </section>
}
