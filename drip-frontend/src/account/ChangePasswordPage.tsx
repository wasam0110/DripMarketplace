import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { AccountGate } from './AccountDetails'
import { validatePasswordChange, type PasswordChange } from './password'

const empty: PasswordChange = { current_password: '', new_password: '', confirm_password: '' }
export function ChangePasswordPage() {
  const auth = useAuth()
  const [success, setSuccess] = useState(false)
  if (success) return <section className="container page"><h1>Password changed</h1><p role="status">Your password was changed. Sign in again with your new password.</p><Link className="button" to="/login">Sign in again</Link></section>
  return <AccountGate title="Change your password">{(owner) => <PasswordForm key={owner} confirmed={() => { auth.clearSession(); setSuccess(true) }} />}</AccountGate>
}
function PasswordForm({ confirmed }: { confirmed: () => void }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [draft, setDraft] = useState(empty)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const lock = useRef(false)
  const active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lock.current || blocked) return
    try { validatePasswordChange(draft) } catch (reason) { setError(reason); return }
    // Preserve exact password characters, never trim, persist or automatically replay them.
    const payload = { ...draft }
    lock.current = true; setBusy(true); setError(null); setDraft(empty)
    try {
      const response = await request<unknown>('/me/change-password', { method: 'POST', authenticated: true, body: JSON.stringify(payload) })
      if (response !== undefined) throw new Error('The password change response could not be confirmed.')
      if (active.current) confirmed()
    } catch (reason) {
      if (!active.current) return
      setError(reason)
      if (!(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500) setBlocked(true)
    } finally {
      payload.current_password = ''; payload.new_password = ''; payload.confirm_password = ''
      lock.current = false
      if (active.current) setBusy(false)
    }
  }
  return <>
    <p>For accounts with a password. Accounts without a local password must use their sign-in provider; the server checks eligibility.</p>
    <p className="notice">Changing your password invalidates existing sessions. You will need to sign in again. No password is stored by this app in browser storage.</p>
    {blocked && <p role="alert" className="notice">The change may have reached the server. Do not submit it again. Sign in with your new password to check; if you cannot sign in, use password reset or contact support. This form stays locked until you leave the page.</p>}
    {Boolean(error) && <ErrorNotice error={error} />}
    <form className="account-card auth-form" onSubmit={submit} aria-busy={busy}>
      <Field label="Current password" type="password" autoComplete="current-password" required disabled={busy || blocked} value={draft.current_password} onChange={(event) => setDraft({ ...draft, current_password: event.target.value })} />
      <Field label="New password" type="password" autoComplete="new-password" required maxLength={128} disabled={busy || blocked} value={draft.new_password} onChange={(event) => setDraft({ ...draft, new_password: event.target.value })} hint="8–128 characters, including uppercase, lowercase and a number. Spaces are preserved." />
      <Field label="Confirm new password" type="password" autoComplete="new-password" required maxLength={128} disabled={busy || blocked} value={draft.confirm_password} onChange={(event) => setDraft({ ...draft, confirm_password: event.target.value })} />
      <Button type="submit" disabled={busy || blocked}>{busy ? 'Changing password…' : 'Change password and sign out'}</Button>
      <Button className="button-secondary" disabled={busy || blocked} onClick={() => { setDraft(empty); setError(null) }}>Clear password fields</Button>
    </form>
    <p className="muted">Password fields are cleared when a request is sent. After a rejected request, enter them again to retry. Do not navigate away while a change is being processed.</p>
    <Button className="button-secondary" disabled={busy} onClick={() => { setDraft(empty); auth.clearSession(); navigate('/login') }}>Clear local session and go to sign in</Button>
    <p className="muted">Clearing this local session alone does not revoke sessions on the server.</p>
  </>
}
