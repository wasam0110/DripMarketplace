import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { refreshSession, request } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { useCart } from '../cart/CartProvider'
import { validateQuote, type CheckoutQuote } from '../checkout/preview'
import { safeWhatsapp } from '../checkout/submission'
import { useSubmission } from '../checkout/useSubmission'
import type { GuestSelection } from '../cart/guestStorage'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useOrderAccess } from '../orders/access'
import { SavedAddressPicker } from '../checkout/SavedAddressPicker'
import { PayFastHandoff } from '../payments/PayFastHandoff'
import { payfastEnabled } from '../payments/payfast'

const provinces = ['Sindh', 'Punjab', 'Islamabad', 'Khyber Pakhtunkhwa', 'Balochistan', 'Gilgit-Baltistan', 'Azad Kashmir']
const emptyDetails = { recipient_name: '', email: '', phone: '', street: '', city: '', province: '', note: '' }

export function CheckoutPage() {
  const auth = useAuth()
  if (auth.loading) return <section className="container page"><p role="status">Checking your session…</p></section>
  if (auth.error) return <section className="container page"><ErrorNotice error={new Error(auth.error)} /><Link to="/login">Sign in to continue</Link></section>
  // Discard contact details and outstanding preview state when the account changes.
  return <CheckoutPreview key={auth.user?.id ?? 'guest'} />
}

function CheckoutPreview() {
  const navigate = useNavigate()
  const orderAccess = useOrderAccess()
  const { user } = useAuth()
  const bag = useCart()
  const [step, setStep] = useState(1)
  const [details, setDetails] = useState(emptyDetails)
  const [quote, setQuote] = useState<CheckoutQuote | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [retry, setRetry] = useState(0)
  const [payment, setPayment] = useState('')
  const [quoteMethod, setQuoteMethod] = useState('cod')
  const [couponCode, setCouponCode] = useState('')
  const [coupon, setCoupon] = useState<string | null>(null)
  const [couponError, setCouponError] = useState<unknown>(null)
  const [couponBusy, setCouponBusy] = useState(false)
  const generation = useRef(0)
  const couponRequest = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const sentBag = useRef<GuestSelection[]>([])
  const submission = useSubmission(user?.id ?? 'guest',
    () => bag.completeCheckout(sentBag.current),
    () => { setStep(1); setRetry((value) => value + 1) })
  const selection = JSON.stringify((user ? bag.cart?.items ?? [] : bag.guest).map(({ variant_id, quantity }) => ({ variant_id, quantity })))
  const ready = !bag.loading && !bag.busy && !bag.needsReview && !bag.error && (user || !bag.storageError)

  useEffect(() => { heading.current?.focus() }, [step])
  useEffect(() => {
    if (submission.blocked || submission.result) return
    const ticket = ++generation.current
    const controller = new AbortController()
    couponRequest.current?.abort()
    setQuote(null); setCoupon(null); setCouponBusy(false); setCouponError(null); setError(null); setPayment(''); setStep(1)
    if (!ready) { setLoading(Boolean(bag.loading || bag.busy)); return }
    if (selection === '[]') { setLoading(false); return }
    setLoading(true)
    async function load() {
      if (user) await refreshSession()
      if (controller.signal.aborted) return
      const result = await request<CheckoutQuote>(user ? '/orders/quote' : '/orders/guest/quote', {
        method: 'POST', authenticated: Boolean(user), signal: controller.signal,
        body: JSON.stringify(user ? { payment_method: quoteMethod } : { items: JSON.parse(selection), payment_method: quoteMethod }),
      })
      if (!controller.signal.aborted && ticket === generation.current) setQuote(validateQuote(result))
    }
    void load().catch((reason: unknown) => {
      if (!controller.signal.aborted && ticket === generation.current) setError(reason)
    }).finally(() => { if (!controller.signal.aborted && ticket === generation.current) setLoading(false) })
    return () => { controller.abort(); couponRequest.current?.abort() }
  }, [selection, ready, retry, user, bag.loading, bag.busy, submission.blocked, submission.result, quoteMethod])

  const cod = quote?.payment_methods.find((method) => method.method === 'cod')
  const payfast = quote?.payment_methods.find((method) => method.method === 'payfast')
  const chosenAvailable = payment === quoteMethod && (payment === 'cod' ? cod?.available === true : payment === 'payfast' && payfastEnabled && payfast?.available === true)
  const total = quote?.total ?? null
  const disabled = loading || !quote || !ready || couponBusy || submission.busy
  function update(field: keyof typeof details, value: string) { setDetails((current) => ({ ...current, [field]: value })) }
  function continueDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (disabled) return
    const trimmed = Object.fromEntries(Object.entries(details).map(([key, value]) => [key, value.trim()])) as typeof details
    if (trimmed.recipient_name.length < 2 || trimmed.street.length < 5 || trimmed.city.length < 2) {
      setError(new Error('Enter a full recipient name, street address and city, not only spaces.')); return
    }
    setDetails(trimmed); setError(null); setStep(2)
  }
  async function applyCoupon(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!user || !quote || disabled || couponBusy) return
    const controller = new AbortController()
    couponRequest.current?.abort(); couponRequest.current = controller
    const ticket = generation.current
    setCouponBusy(true); setCouponError(null)
    try {
      await refreshSession()
      if (controller.signal.aborted) return
      const result = await request<CheckoutQuote>('/orders/quote', {
        method: 'POST', authenticated: true, signal: controller.signal,
        body: JSON.stringify({ coupon_code: couponCode.trim(), payment_method: quoteMethod }),
      })
      validateQuote(result)
      if (!controller.signal.aborted && ticket === generation.current) {
        setQuote(result); setCoupon(couponCode.trim().toUpperCase()); setStep(1); setPayment('')
      }
    } catch (reason) { if (!controller.signal.aborted && ticket === generation.current) setCouponError(reason) }
    finally { if (!controller.signal.aborted && ticket === generation.current) setCouponBusy(false) }
  }

  function placeOrder() {
    if (disabled || !quote || !chosenAvailable || step !== 3) return
    if (Date.parse(quote.quote_expires_at) <= Date.now()) {
      setError(new Error('Your quote expired. Review refreshed prices before placing your order.'))
      setRetry((value) => value + 1); return
    }
    const { email, ...shipping_address } = details
    sentBag.current = bag.guest.map((item) => ({ ...item }))
    submission.submit({
      shipping_address, payment_method: payment, quote_token: quote.quote_token,
      ...(coupon ? { coupon_code: coupon } : {}),
      ...(!user ? { guest_email: email, guest_name: details.recipient_name, guest_phone: details.phone,
        items: quote.items.map(({ variant_id, quantity }) => ({ variant_id, quantity })) } : {}),
    })
  }

  if (submission.result) {
    const order = submission.result
    const whatsapp = safeWhatsapp(order.whatsapp_url)
    return <section className="container page checkout-page">
      <p className="eyebrow">Order received</p><h1>Your order: {order.order_number}</h1>
      <p role="status">Status: {order.status.replaceAll('_', ' ')}</p>
      <p>Total: {formatPrice(order.total)} · {order.payment_method === 'cod' ? 'Cash on delivery' : 'PayFast'}</p>
      {order.status === 'pending_cod_verification' && <p>Verification is required before your order can be processed. No online payment was taken.</p>}
      {order.payment_method === 'cod' && whatsapp && <a className="button" href={whatsapp} target="_blank" rel="noopener noreferrer">Continue verification on WhatsApp</a>}
      {order.payment_method === 'payfast' && <PayFastHandoff key={order.order_id} order={order} account={Boolean(user)} recovered={submission.recovered} />}
      <Button className="button-secondary" disabled={!user && !order.guest_token} onClick={() => {
        if (!user && order.guest_token) orderAccess.remember({ id: order.order_id, token: order.guest_token })
        navigate(`/orders/${encodeURIComponent(order.order_id)}`)
      }}>View order details</Button>
      <p>Keep your order number. This tab can recover your order; guest recovery is available for 24 hours. Do not share this tab’s saved checkout key.</p>
      {!user && <p>Review your saved bag before another order, especially if this order was recovered after a reload.</p>}
      {Boolean(bag.storageError || submission.error) && <ErrorNotice error={submission.error || bag.storageError} />}
      {order.payment_method === 'cod' && <Button className="button-secondary" onClick={submission.startAnother}>Review bag for another order</Button>}
    </section>
  }
  if (submission.blocked) return <section className="container page checkout-page">
    <h1>{submission.busy ? 'Checking your order…' : 'Recover your checkout'}</h1>
    <p role="status">Do not place a separate order while this attempt is unresolved. Recovery and retry use the same checkout key.</p>
    {Boolean(submission.error) && <ErrorNotice error={submission.error} />}
    {submission.canRecover && <Button disabled={submission.busy} onClick={submission.recover}>Check order status</Button>}
    {submission.canRetry && <Button className="button-secondary" disabled={submission.busy} onClick={submission.retry}>Retry the same order</Button>}
    <p>After a reload, check the order status first. Contact support if guest recovery has expired; do not start a replacement order.</p>
  </section>

  return <section className="container page checkout-page">
    <Link className="text-link" to="/bag">Back to your bag</Link>
    <p className="eyebrow">Checkout</p>
    <h1 ref={heading} tabIndex={-1}>{step === 1 ? 'Where should we send it?' : step === 2 ? 'Choose your payment' : 'One last look'}</h1>
    <p className="lead">{user ? 'Contact and delivery for your account bag.' : 'Guest checkout, with your own point of view.'}</p>
    <ol className="checkout-steps" aria-label="Checkout progress">{['Details', 'Payment', 'Review'].map((label, index) =>
      <li key={label} aria-current={step === index + 1 ? 'step' : undefined}>{index + 1} · {label}</li>)}</ol>
    <p className="notice">{payfastEnabled ? 'Review the final total before creating an order. PayFast payment requires a separate explicit handoff. Changing payment method refreshes the quote and restarts review; reapply any coupon.' : 'Place a cash-on-delivery order after reviewing the final total. Online payments remain disabled.'}</p>
    {Boolean(submission.error) && <ErrorNotice error={submission.error} />}
    {Boolean(error || bag.error || (!user && bag.storageError)) && <ErrorNotice error={error || bag.error || bag.storageError} />}
    {bag.needsReview && <p role="alert">Review the last bag update before checkout. <Link to="/bag">Return to your bag</Link></p>}
    {loading && <p role="status">Checking current prices, delivery and availability…</p>}
    {!loading && !quote && !error && ready && <EmptyState title="Your bag needs a first piece."><Link to="/clothing">Explore clothing</Link></EmptyState>}
    {Boolean(error) && <Button disabled={loading} onClick={() => setRetry((value) => value + 1)}>Retry checkout preview</Button>}
    {quote && ready && <div className="bag-layout">
      <div className="checkout-content">
        {step === 1 && <form onSubmit={continueDetails} className="checkout-form">
          <h2>{user ? 'Contact and delivery' : 'Checkout as a guest'}</h2>
          {!user && <><Field label="Email address" type="email" autoComplete="email" required maxLength={254} value={details.email} onChange={(event) => update('email', event.target.value)} />
            <Link className="text-link" to="/login">Sign in instead</Link></>}
          {user && <p>Signed in as {user.email}</p>}
          {user && <SavedAddressPicker disabled={disabled} onUse={(address) => { setDetails((current) => ({ ...current, ...address })); setError(null) }} />}
          <Field label="Recipient name" autoComplete="shipping name" required minLength={2} maxLength={200} value={details.recipient_name} onChange={(event) => update('recipient_name', event.target.value)} />
          <Field label="Mobile number" type="tel" autoComplete="shipping tel" required maxLength={20} pattern="(\+92|0)?3[0-9]{9}" hint="Use 03001234567 or +923001234567, without spaces." value={details.phone} onChange={(event) => update('phone', event.target.value)} />
          <Field label="Street address" autoComplete="shipping street-address" required minLength={5} maxLength={500} value={details.street} onChange={(event) => update('street', event.target.value)} />
          <div className="name-fields"><Field label="City" autoComplete="shipping address-level2" required minLength={2} maxLength={100} value={details.city} onChange={(event) => update('city', event.target.value)} />
            <div className="field"><label htmlFor="checkout-province">Province</label><select id="checkout-province" required autoComplete="shipping address-level1" value={details.province} onChange={(event) => update('province', event.target.value)}>
              <option value="">Choose province</option>{details.province && !provinces.includes(details.province) && <option value={details.province}>{details.province}</option>}{provinces.map((province) => <option key={province}>{province}</option>)}
            </select></div></div>
          <Field label="Delivery note (optional)" maxLength={500} value={details.note} onChange={(event) => update('note', event.target.value)} />
          <p className="muted">These details stay in this page’s memory. They are not saved or sent while previewing.</p>
          <Button type="submit" disabled={disabled}>Continue to payment</Button>
        </form>}
        {step === 2 && <div className="checkout-form"><h2>Choose how to pay</h2>
          <fieldset className="payment-options"><legend className="sr-only">Payment method</legend>
            <label className="payment-option"><input type="radio" name="payment" value="cod" disabled={disabled || !cod?.available} checked={payment === 'cod'} onChange={() => { if (quoteMethod !== 'cod') { setQuote(null); setLoading(true); setQuoteMethod('cod') } else setPayment('cod') }} />
              <span>Cash on delivery<small>{cod?.available ? 'Verification is required before processing. Pay on delivery.' : cod?.unavailable_reason || 'Cash on delivery is unavailable.'}</small></span></label>
            <label className="payment-option"><input type="radio" name="payment" value="payfast" disabled={disabled || !payfastEnabled || payfast?.available !== true} checked={payment === 'payfast'} onChange={() => { if (quoteMethod !== 'payfast') { setQuote(null); setLoading(true); setQuoteMethod('payfast') } else setPayment('payfast') }} /><span>Pay online · PayFast<small>{!payfastEnabled ? 'Online payment initiation is not enabled in this frontend.' : payfast?.available ? 'Create the order, then explicitly continue to PayFast. Changing method refreshes your quote.' : payfast?.unavailable_reason || 'PayFast is unavailable.'}</small></span></label>
          </fieldset>
          <Button disabled={!chosenAvailable || disabled} onClick={() => setStep(3)}>Review your order</Button>
          <Button className="button-secondary" onClick={() => setStep(1)}>Back to details</Button>
        </div>}
        {step === 3 && <div className="checkout-form"><h2>Your pieces</h2>
          {quote.items.map((item) => <article className="checkout-review-item" key={item.variant_id}><p className="eyebrow">{item.brand_name}</p><h3>{item.product_name}</h3><p>{item.size} · {item.colour} · Qty {item.quantity}</p><p>{formatPrice(item.subtotal)}</p></article>)}
          <h2>Delivery & payment</h2><address>{details.recipient_name}<br />{details.street}<br />{details.city}, {details.province}<br />{details.phone}<br />{user?.email || details.email}</address>
          {details.note && <p>{details.note}</p>}<p>{payment === 'payfast' ? 'PayFast · order creation does not confirm payment.' : 'Cash on delivery · verification pending until an order is placed.'}</p>
          <div className="option-row"><Button className="button-secondary" onClick={() => setStep(1)}>Edit details</Button><Button className="button-secondary" onClick={() => setStep(2)}>Change payment</Button></div>
          <Button disabled={disabled || !chosenAvailable} onClick={placeOrder}>Place order · {formatPrice(total!)}</Button>
          <p className="notice">By placing this order, you accept the displayed items and total. Changed prices require a fresh review.</p>
        </div>}
      </div>
      <aside className="bag-summary" aria-labelledby="checkout-summary"><h2 id="checkout-summary">Order summary</h2>
        <dl><div><dt>Subtotal · {quote.item_count} pieces</dt><dd>{formatPrice(quote.subtotal)}</dd></div><div><dt>Delivery</dt><dd>{formatPrice(quote.shipping_fee)}</dd></div>
          <div><dt>Discount</dt><dd>{formatPrice(quote.discount_amount)}</dd></div><div className="bag-total"><dt>Order total</dt><dd>{formatPrice(total!)}</dd></div></dl>
        <p>Each brand fulfils its own pieces. This is a current estimate, not a reserved price or stock allocation.</p>
        {user ? <form className="checkout-form" onSubmit={(event) => void applyCoupon(event)}>
          <Field label="Promo code" maxLength={30} required value={couponCode} disabled={couponBusy} onChange={(event) => { setCouponCode(event.target.value); setCouponError(null) }} />
          <Button className="button-secondary" type="submit" disabled={disabled || couponBusy || !couponCode.trim()}>{couponBusy ? 'Checking code…' : 'Apply code'}</Button>
          {coupon && <><p role="status">{coupon} applied to this quote.</p><Button className="button-secondary" disabled={couponBusy} onClick={() => { setCouponCode(''); setRetry((value) => value + 1) }}>Remove code</Button></>}
          {Boolean(couponError) && <ErrorNotice error={couponError} />}
        </form> : <p><Link className="text-link" to="/login">Sign in to use a promo code</Link></p>}
        <Button className="button-secondary" disabled={loading || couponBusy} onClick={() => setRetry((value) => value + 1)}>Refresh prices</Button>
        <small>Refreshing restarts the review and removes any coupon. The server checks COD availability after discounts.</small>
      </aside>
    </div>}
  </section>
}
