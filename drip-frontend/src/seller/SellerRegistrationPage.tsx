import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { extraSlots, registrationMarker, registrationMoney, samePricing, validateRegistrationPricing, validateRegistrationResult, type RegistrationPricing, type RegistrationResult } from './registration'

const blank = { first_name: '', last_name: '', email: '', password: '', brand_name: '', description: '', return_policy: '', whatsapp_number: '', instagram_handle: '' }

export function SellerRegistrationPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Sell with WearHowZ</h1><p role="status">Checking your session…</p></section>
  if (error) return <section className="container page"><h1>Session unavailable</h1><ErrorNotice error={new Error(error)} /><Link to="/login">Return to sign in</Link></section>
  if (user) return <section className="container page"><h1>You are already signed in</h1>
    <p>Seller registration creates a new account; it does not convert your current account. Sign out before starting a new application.</p>
    <Link className="button" to={accountDestination(user.role)}>Return to your workspace</Link><p><Link to="/account">Account settings and sign out</Link></p>
  </section>
  return <RegistrationForm />
}

function Pricing({ value }: { value: RegistrationPricing }) {
  return <dl>
    <dt>Registration fee</dt><dd>{registrationMoney(value.registration_fee)}</dd>
    <dt>Included listing slots</dt><dd>{value.base_slots}</dd>
    <dt>Price per extra slot</dt><dd>{registrationMoney(value.extra_slot_price)}</dd>
    <dt>Extra slots</dt><dd>{value.extra_slots}</dd>
    <dt>Extra slot cost</dt><dd>{registrationMoney(value.extra_cost)}</dd>
    <dt>Total listing slots</dt><dd>{value.total_slots}</dd>
    <dt>Registration total preview</dt><dd>{registrationMoney(value.total_cost)}</dd>
  </dl>
}

function RegistrationForm() {
  const [draft, setDraft] = useState(blank)
  const [slots, setSlots] = useState('0')
  const count = extraSlots(slots)
  const path = `/seller/register/slot-price?extra_slots=${count ?? 0}`
  const validate = useCallback((value: RegistrationPricing) => validateRegistrationPricing(value, count ?? 0), [count])
  const pricing = useOrderRead(path, false, validate)
  const [review, setReview] = useState<RegistrationPricing | null>(null)
  const [result, setResult] = useState<RegistrationResult | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(() => {
    try { return sessionStorage.getItem(registrationMarker) !== null } catch { return true }
  })
  const lock = useRef(false)
  const alive = useRef(true)
  const stepHeading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  useEffect(() => { stepHeading.current?.focus() }, [review, result, blocked])
  const fields = error instanceof ApiError ? error.fields : {}
  const update = (name: keyof typeof blank, value: string) => { setDraft((current) => ({ ...current, [name]: value })); setReview(null); setError(null) }

  function reviewApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lock.current || blocked || pricing.loading || !pricing.data || count === null) return
    if ([draft.first_name, draft.brand_name, draft.description, draft.return_policy].some((value) => !value.trim())) {
      setError(new Error('Complete the required application fields.')); return
    }
    setError(null); setReview(pricing.data)
  }

  async function submit() {
    if (lock.current || blocked || !review || count === null) return
    lock.current = true; setBusy(true); setError(null)
    let sent = false
    try {
      const current = validateRegistrationPricing(await request<RegistrationPricing>(path, { cache: 'no-store' }), count)
      if (!alive.current) return
      if (!samePricing(review, current)) {
        setReview(null); pricing.retry()
        throw new Error('Pricing changed. Review the updated server prices before submitting.')
      }
      // Persist only a non-secret guard; never store the application or its password.
      if (sessionStorage.getItem(registrationMarker) !== null) { setBlocked(true); return }
      sessionStorage.setItem(registrationMarker, 'pending')
      sent = true
      const response = validateRegistrationResult(await request<RegistrationResult>('/seller/register', {
        method: 'POST', body: JSON.stringify({ ...draft, first_name: draft.first_name.trim(),
          last_name: draft.last_name.trim() || null, email: draft.email.trim(), brand_name: draft.brand_name.trim(),
          description: draft.description.trim(), return_policy: draft.return_policy.trim(),
          whatsapp_number: draft.whatsapp_number.trim(), instagram_handle: draft.instagram_handle.trim() || null, extra_slots: count }),
      }))
      if (alive.current) { setResult(response); setDraft(blank) }
    } catch (reason) {
      if (!alive.current) return
      if (sent && reason instanceof ApiError && [409, 422].includes(reason.status)) {
        try { sessionStorage.removeItem(registrationMarker) } catch { setBlocked(true) }
        setReview(null)
      } else if (sent) setBlocked(true)
      setError(reason)
    } finally {
      if (alive.current) { setBusy(false); if (sent) setDraft((current) => ({ ...current, password: '' })) }
      lock.current = false
    }
  }

  return <section className="container page account-page">
    <p className="eyebrow">For independent labels</p><h1>Sell with WearHowZ</h1>
    <p className="lead">Introduce your label. Review your registration, then apply.</p>
    {result ? <div className="account-card" role="status">
      <h2 ref={stepHeading} tabIndex={-1}>Application received</h2><p>{result.message}</p>
      <dl><dt>Application reference</dt><dd>{result.seller_id}</dd><dt>Registration amount due</dt><dd>{registrationMoney(result.amount_due)}</dd></dl>
      {review && Number(result.amount_due) !== Number(review.total_cost) && <p className="notice">The server returned a different amount from the preview. Check the registration amount with support before making a transfer.</p>}
      <p>No payment was collected here, and registration is not brand approval. Check your email for verification instructions. If no email arrives, contact support; do not submit again.</p>
      <Link className="button" to="/login">Sign in to your seller account</Link>
    </div> : blocked ? <div className="account-card">
      <h2 ref={stepHeading} tabIndex={-1}>Check an existing application first</h2>
      <p>A submission may already exist, or this tab cannot safely save its submission guard. No further registration will be sent from this page. Check your verification email, sign in or contact support before trying again.</p>
      <p>Reloading does not resolve an uncertain submission. This tab guard is not a server guarantee and does not coordinate other tabs or devices.</p>
      {Boolean(error) && <ErrorNotice error={error} />}
      <Link className="button" to="/login">Sign in or check your account</Link>
    </div> : <>
      <p>Already applied? <Link to="/login">Sign in</Link>. Registration creates a separate seller account and cannot reuse an existing account email.</p>
      <form className="account-card auth-form" onSubmit={reviewApplication} aria-busy={busy}>
        <h2>Your account and label</h2>
        <fieldset className="auth-form review-fields" disabled={busy || Boolean(review)}>
          <legend>Application details</legend>
          <Field label="First name" required minLength={1} maxLength={100} autoComplete="given-name" value={draft.first_name} onChange={(e) => update('first_name', e.target.value)} error={fields.first_name} />
          <Field label="Last name (optional)" maxLength={100} autoComplete="family-name" value={draft.last_name} onChange={(e) => update('last_name', e.target.value)} error={fields.last_name} />
          <Field label="Email address" required type="email" maxLength={254} autoComplete="email" value={draft.email} onChange={(e) => update('email', e.target.value)} error={fields.email} />
          <Field label="Password" required type="password" minLength={8} maxLength={128} autoComplete="new-password" pattern="(?=.*[A-Z])(?=.*[0-9]).{8,128}" hint="8–128 characters, including an uppercase letter and a number." value={draft.password} onChange={(e) => update('password', e.target.value)} error={fields.password} />
          <Field label="Brand name" required minLength={2} maxLength={100} value={draft.brand_name} onChange={(e) => update('brand_name', e.target.value)} error={fields.brand_name} />
          {(['description', 'return_policy'] as const).map((name) => <div className="field" key={name}>
            <label htmlFor={`seller-${name}`}>{name === 'description' ? 'Brand description' : 'Return policy'}</label>
            <textarea id={`seller-${name}`} required minLength={10} maxLength={name === 'description' ? 2000 : 1000} rows={4} value={draft[name]} onChange={(e) => update(name, e.target.value)} aria-invalid={Boolean(fields[name])} aria-describedby={fields[name] ? `seller-${name}-error` : undefined} />
            {fields[name] && <small className="field-error" id={`seller-${name}-error`}>{fields[name]}</small>}
          </div>)}
          <Field label="WhatsApp mobile number" required type="tel" maxLength={20} pattern="(\+92|0)?3[0-9]{9}" hint="Pakistani mobile number: 03XXXXXXXXX or +923XXXXXXXXX." autoComplete="tel" value={draft.whatsapp_number} onChange={(e) => update('whatsapp_number', e.target.value)} error={fields.whatsapp_number} />
          <Field label="Instagram handle (optional)" maxLength={100} value={draft.instagram_handle} onChange={(e) => update('instagram_handle', e.target.value)} error={fields.instagram_handle} />
          <Field label="Extra listing slots" required type="number" min={0} max={10000} step={1} value={slots} onChange={(e) => { setSlots(e.target.value); setReview(null); setError(null) }} error={count === null ? 'Enter a whole number from 0 to 10,000.' : fields.extra_slots} />
        </fieldset>
        {Boolean(error) && <ErrorNotice error={error} />}
        {pricing.loading && <p role="status">Loading current registration pricing…</p>}
        {Boolean(pricing.error) && <ErrorNotice error={pricing.error} />}
        {count !== null && pricing.data && <Pricing value={review ?? pricing.data} />}
        <p className="notice">Prices are a preview, not a locked quote. The server sets the final amount when you apply; no payment is collected by this form. Verify the returned amount before arranging any transfer. Approval is separate.</p>
        {review ? <div className="auth-form">
          <h2 ref={stepHeading} tabIndex={-1}>Review your application</h2><p>Apply for {draft.brand_name} using {draft.email}. Check the details and pricing above before submitting.</p>
          <Button disabled={busy} onClick={() => void submit()}>{busy ? 'Submitting application…' : 'Submit seller application'}</Button>
          <Button className="button-secondary" disabled={busy} onClick={() => setReview(null)}>Edit application</Button>
        </div> : <>
          <Button type="submit" disabled={busy || pricing.loading || !pricing.data || count === null}>Review application</Button>
          <Button className="button-secondary" disabled={pricing.loading || busy} onClick={pricing.retry}>Refresh registration pricing</Button>
        </>}
      </form>
      <p className="muted">Your draft stays in memory and is discarded when you leave. After submitting, this tab blocks repeat applications if the result is uncertain. No password or application details are saved by this page.</p>
    </>}
  </section>
}
