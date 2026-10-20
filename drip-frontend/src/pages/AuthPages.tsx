import { useState, type FormEvent } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import type { AuthResponse } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Arrow, Button, EmptyState, ErrorNotice, Field } from '../components/ui'

type Mode = 'login' | 'register' | 'forgot' | 'reset'
const headings: Record<Mode, [string, string, string]> = {
  login: ['Welcome back.', 'Sign in to your WearHowZ account.', 'Sign in'],
  register: ['Your style starts here.', 'Create your WearHowZ account.', 'Create account'],
  forgot: ['Forgot your password?', 'Enter your email and we’ll guide you through the next step.', 'Send reset instructions'],
  reset: ['Make a fresh start.', 'Choose a new password for your account.', 'Reset password'],
}

export function AuthPage({ mode }: { mode: Mode }) {
  const auth = useAuth()
  const [params] = useSearchParams()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [message, setMessage] = useState('')
  const [admin, setAdmin] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [title, description, submitLabel] = headings[mode]
  const fields = error instanceof ApiError ? error.fields : {}
  const token = params.get('token')
  if (auth.user && mode === 'login') return <Navigate to="/account" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '')
    setBusy(true); setError(null)
    try {
      if (mode === 'login') {
        await auth.signIn(value('email').trim(), value('password'), admin ? value('totp') : undefined)
      } else if (mode === 'register') {
        await request('/auth/register', { method: 'POST', body: JSON.stringify({
          first_name: value('first_name').trim(), last_name: value('last_name').trim(),
          email: value('email').trim(), password: value('password'),
        }) })
        setMessage('Your inbox has the next step. Open the verification link in your email to finish setting up your account.')
      } else if (mode === 'forgot') {
        await request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email: value('email').trim() }) })
        setMessage('If an account exists for that email, you’ll receive a password-reset link shortly.')
      } else {
        if (!token) throw new Error('This reset link is missing its token. Request a new password-reset email.')
        if (value('password') !== value('confirmation')) throw new Error('The passwords don’t match.')
        await request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password: value('password') }) })
        auth.clearSession()
        setMessage('Your password is updated. Sign in with your new password.')
        window.history.replaceState(null, '', '/reset-password')
      }
    } catch (reason) { setError(reason) }
    finally { setBusy(false) }
  }

  return <section className="auth-layout container">
    <div className="auth-art"><img src="/assets/editorial.png" alt="Independent fashion, photographed in warm natural light" />
      <div><p className="eyebrow">Independent style</p><h2>Your wardrobe.<br /><em>Your world.</em></h2></div>
    </div>
    <div className="auth-content">
      <p className="eyebrow">Your WearHowZ account</p><h1>{title}</h1><p className="lead">{description}</p>
      {message ? <div className="notice" role="status"><p>{message}</p><Link className="text-link" to="/login">Back to sign in <Arrow /></Link></div>
        : <form onSubmit={submit} className="auth-form" aria-busy={busy}>
          {mode === 'register' && <div className="name-fields">
            <Field label="First name" name="first_name" autoComplete="given-name" required minLength={2} maxLength={100} error={fields.first_name} />
            <Field label="Last name" name="last_name" autoComplete="family-name" required minLength={2} maxLength={100} error={fields.last_name} />
          </div>}
          {mode !== 'reset' && <Field label="Email address" name="email" type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com" error={fields.email} />}
          {mode !== 'forgot' && <>
            <Field label={mode === 'reset' ? 'New password' : 'Password'} name="password" type={showPassword ? 'text' : 'password'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required maxLength={128}
              minLength={mode === 'login' ? undefined : 8} error={fields.password ?? fields.new_password}
              pattern={mode === 'login' ? undefined : '(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).{8,128}'}
              hint={mode === 'login' ? undefined : '8–128 characters, including uppercase, lowercase and a number.'} />
            <label className="checkbox-label"><input type="checkbox" checked={showPassword} onChange={(event) => setShowPassword(event.target.checked)} />Show password</label>
          </>}
          {mode === 'reset' && <Field label="Confirm password" name="confirmation" type="password" autoComplete="new-password" required maxLength={128} />}
          {mode === 'login' && <>
            <Link className="text-link forgot-link" to="/forgot-password">Forgot password?</Link>
            <label className="checkbox-label admin-choice"><input type="checkbox" checked={admin} onChange={(event) => setAdmin(event.target.checked)} />Administrator sign-in</label>
            {admin && <Field label="Administrator authenticator code" name="totp" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} minLength={6} autoComplete="one-time-code" required hint="Only administrator accounts require this additional check." />}
          </>}
          {error ? <ErrorNotice error={error} /> : null}
          <Button type="submit" disabled={busy || auth.loading || (mode === 'reset' && !token)}>{busy ? 'Please wait…' : submitLabel} <Arrow /></Button>
          {mode === 'reset' && !token && <p className="field-error">Open the link from your password-reset email, or <Link to="/forgot-password">request a new link</Link>.</p>}
        </form>}
      {mode === 'login' && <>
        <div className="auth-divider">or continue with</div>
        <Button className="button-secondary google-button" disabled={busy || auth.loading || import.meta.env.VITE_ENABLE_GOOGLE_AUTH !== 'true'}
          onClick={async () => {
            setBusy(true); setError(null)
            try {
              const result = await request<{ authorization_url: string }>('/auth/google')
              const target = new URL(result.authorization_url)
              if (target.protocol !== 'https:' || target.hostname !== 'accounts.google.com') throw new Error('The sign-in provider returned an unexpected address.')
              window.location.assign(target.href)
            } catch (reason) { setError(reason); setBusy(false) }
          }}>Continue with Google</Button>
        {import.meta.env.VITE_ENABLE_GOOGLE_AUTH !== 'true' && <small className="muted google-note">Google sign-in awaits local provider and callback configuration.</small>}
      </>}
      {mode === 'login' && <p className="auth-switch">New to WearHowZ? <Link className="text-link" to="/register">Create an account</Link></p>}
      {mode !== 'login' && !message && <p className="auth-switch"><Link className="text-link" to="/login">Back to sign in</Link></p>}
      <p className="auth-footnote">One account. Your favourite labels, saved pieces and orders.</p>
    </div>
  </section>
}

export function VerifyEmailPage() {
  const { acceptSession, loading } = useAuth()
  const [params] = useSearchParams()
  const [busy, setBusy] = useState(false)
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const token = params.get('token')
  return <section className="container page">
    <EmptyState title={complete ? 'You’re all set.' : 'One last step.'}>
      <p>{complete ? 'Your email is verified and you’re signed in.' : 'Confirm your email to finish setting up your WearHowZ account.'}</p>
    </EmptyState>
    <div className="verification-actions">
      {error ? <ErrorNotice error={error} /> : null}
      {complete ? <Link className="button" to="/account">Continue to your account <Arrow /></Link>
        : token ? <Button disabled={busy || loading} onClick={async () => {
          setBusy(true); setError(null)
          try {
            // An explicit action avoids consuming a single-use token twice in StrictMode.
            const session = await request<AuthResponse>(`/auth/verify-email?token=${encodeURIComponent(token)}`)
            acceptSession(session); setComplete(true)
            window.history.replaceState(null, '', '/verify-email')
          } catch (reason) { setError(reason) } finally { setBusy(false) }
        }}>{busy ? 'Verifying…' : 'Verify my email'}</Button>
          : <p>This verification link is missing its token. Open the full link from your email.</p>}
    </div>
  </section>
}

export function AccountPage() {
  const { user, loading, error: restoreError, signOut } = useAuth()
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  if (loading) return <div className="container page" role="status">Restoring your session…</div>
  if (!user) return <section className="container page">
    <EmptyState title="Let’s get you back in."><p>{restoreError ?? 'Sign in to continue to your account.'}</p><Link className="button" to="/login">Sign in <Arrow /></Link></EmptyState>
  </section>
  return <section className="container page account-page">
    <p className="eyebrow">Your WearHowZ account</p><h1>Welcome, {user.first_name || 'back'}.</h1>
    <div className="account-card"><h2>Your account</h2><dl><dt>Email</dt><dd>{user.email}</dd><dt>Account type</dt><dd>{user.role}</dd>
      <dt>Email status</dt><dd>{user.has_verified_email ? 'Verified' : 'Verification needed'}</dd></dl>
      <p className="muted">The account dashboard, orders and role-specific portals are part of the next build steps.</p>
      {error ? <ErrorNotice error={error} /> : null}
      <Button disabled={busy} onClick={async () => {
        setBusy(true); setError(null)
        try { await signOut() } catch (reason) { setError(reason) } finally { setBusy(false) }
      }}>{busy ? 'Signing out…' : 'Sign out'}</Button>
    </div>
  </section>
}
