import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { AccountGate } from './AccountDetails'

export function DeleteAccountPage() {
  const auth = useAuth()
  const [done, setDone] = useState(false)
  if (done) return <section className="container page"><h1>Account deletion confirmed</h1><p role="status">Your account is disabled and your local session has been cleared. Financial and dispute records remain. External cache and image cleanup may finish later.</p><p>Device-local saved pieces and guest bag data are separate and have not been erased.</p><Link className="button" to="/">Back to the store</Link></section>
  return <AccountGate title="Delete your account">{(owner) => auth.user?.role === 'customer'
    ? <DeletionForm key={owner} confirmed={() => { auth.clearSession(); setDone(true) }} />
    : <p className="notice">Seller and administrator accounts require managed offboarding. Account deletion is not available here.</p>}</AccountGate>
}

function DeletionForm({ confirmed }: { confirmed: () => void }) {
  const [password, setPassword] = useState('')
  const [phrase, setPhrase] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const lock = useRef(false)
  const active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lock.current || blocked || !reviewed || !password || phrase.trim() !== 'DELETE MY ACCOUNT') return
    lock.current = true; setBusy(true); setError(null)
    const payload = { password, confirm_phrase: phrase.trim() }
    setPassword(''); setPhrase(''); setReviewed(false)
    try {
      const response = await request<unknown>('/customers/me', { method: 'DELETE', authenticated: true, body: JSON.stringify(payload) })
      if (response !== undefined) throw new Error('The deletion response could not be confirmed.')
      if (active.current) confirmed()
    } catch (reason) {
      if (!active.current) return
      setError(reason)
      if (!(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500) setBlocked(true)
    } finally {
      payload.password = ''
      lock.current = false
      if (active.current) setBusy(false)
    }
  }
  return <>
    <p>This disables your customer account and removes profile credentials and saved addresses. There is no restore action on this page.</p>
    <div className="notice"><h2>What stays, and what is removed</h2><p>Orders, payments, refunds and dispute records are retained, together with an internal identity key. This is not erasure of every record.</p><p>Review text and photo links, notifications and notification preferences are removed. Review ratings and status remain. Account cart/wishlist caches and eligible uploaded images are queued for cleanup; physical deletion is not immediate.</p><p>Device-local saved pieces and guest bag data are not removed by this action.</p></div>
    <p>Active orders, open returns/disputes and pending refunds block deletion. The server checks these when you submit. A local password is required; if your account has none, resolve password access before continuing.</p>
    <p><Link to="/orders">Review your orders</Link> · <Link to="/returns">Review your returns</Link></p>
    {blocked && <p role="alert" className="notice">Deletion could not be confirmed and may already have happened. Do not submit again. Contact support to resolve the outcome. This form is locked until you leave the page; reloading does not prove deletion failed.</p>}
    {Boolean(error) && <ErrorNotice error={error} />}
    <form className="account-card auth-form" onSubmit={submit} aria-busy={busy}>
      <Field label="Current password" type="password" autoComplete="current-password" required disabled={busy || blocked} value={password} onChange={(event) => setPassword(event.target.value)} />
      <Field label="Type DELETE MY ACCOUNT" autoComplete="off" required disabled={busy || blocked} value={phrase} onChange={(event) => setPhrase(event.target.value)} />
      <label className="checkbox-label"><input type="checkbox" checked={reviewed} disabled={busy || blocked} onChange={(event) => setReviewed(event.target.checked)} />I understand that access ends and some records are retained.</label>
      <Button type="submit" disabled={busy || blocked || !password || phrase.trim() !== 'DELETE MY ACCOUNT' || !reviewed}>{busy ? 'Deleting account…' : 'Permanently disable my account'}</Button>
      <Button className="button-secondary" disabled={busy || blocked} onClick={() => { setPassword(''); setPhrase(''); setReviewed(false); setError(null) }}>Clear confirmation</Button>
    </form>
    <p className="muted">Confirmation fields clear when submitted. Passwords are not stored in browser storage. Do not navigate away while deletion is processing.</p>
  </>
}
