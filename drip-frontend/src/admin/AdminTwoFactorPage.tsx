import { useState } from 'react'
import { Link } from 'react-router'
import { request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'

interface TOTPSetup { secret: string; qr_uri: string; message: string }
const validSetup = (value: TOTPSetup) => {
  if (!value || typeof value.secret !== 'string' || !value.secret.trim() || typeof value.qr_uri !== 'string' || !value.qr_uri.startsWith('otpauth://totp/') || typeof value.message !== 'string' || !value.message.trim()) throw new Error('Authenticator setup could not be verified. Do not continue until you can inspect a fresh setup.')
  return value
}
const validMessage = (value: { message?: unknown }) => {
  if (!value || typeof value.message !== 'string' || !value.message.trim()) throw new Error('Two-factor enablement could not be confirmed.')
  return value
}
export function AdminTwoFactorPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Admin two-factor authentication</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage two-factor authentication</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Account security</p><h1>Admin two-factor authentication</h1><TwoFactorSetup enabled={user.is_2fa_enabled === true} /></section>
}
function TwoFactorSetup({ enabled }: { enabled: boolean }) {
  const [setup, setSetup] = useState<TOTPSetup | null>(null), [code, setCode] = useState(''), [complete, setComplete] = useState(enabled), [error, setError] = useState<unknown>(null)
  const setupWrite = useAccountWrite(), verifyWrite = useAccountWrite()
  function generate() { void setupWrite.run(async () => validSetup(await request<TOTPSetup>('/auth/setup-2fa', { authenticated: true, method: 'POST' })), setSetup, 'Authenticator setup generated. The secret remains only in this page memory.') }
  function verify() { if (!setup || !/^\d{6}$/.test(code.trim())) { setError(new Error('Enter the six-digit code shown by your authenticator app.')); return } setError(null); void verifyWrite.run(async () => validMessage(await request<{ message?: unknown }>('/auth/setup-2fa/verify', { authenticated: true, method: 'POST', body: JSON.stringify({ code: code.trim() }) })), () => { setComplete(true); setSetup(null); setCode('') }, 'Two-factor authentication enabled. Future admin logins require an authenticator code.') }
  if (complete) return <section className="account-card"><h2>Two-factor authentication is enabled</h2><p>Admin sign-in requires a current six-digit authenticator code. No secret or recovery code is stored by this frontend.</p><Link className="text-link" to="/admin">Return to admin workspace</Link></section>
  return <section className="account-card"><h2>Protect this administrator account</h2><p>Use an authenticator app. Enrollment is not active until a valid six-digit code is verified. Keep the setup key private and do not send it to support.</p><WriteFeedback state={setupWrite} /><WriteFeedback state={verifyWrite} />{!setup ? <Button disabled={setupWrite.busy || setupWrite.blocked} onClick={generate}>Generate authenticator setup</Button> : <><p>Enter this key manually in your authenticator app:</p><p><code>{setup.secret}</code></p><details><summary>Authenticator URI</summary><p style={{ overflowWrap: 'anywhere' }}><code>{setup.qr_uri}</code></p></details><p>{setup.message}</p><Field label="Six-digit authenticator code" inputMode="numeric" value={code} maxLength={6} disabled={verifyWrite.busy || verifyWrite.blocked} onChange={(event) => setCode(event.target.value)} hint="Enrollment uses the current code from your authenticator app." />{Boolean(error) && <ErrorNotice error={error} />}<Button disabled={verifyWrite.busy || verifyWrite.blocked} onClick={verify}>Enable two-factor authentication</Button><Button className="button-secondary" disabled={verifyWrite.busy} onClick={() => { setSetup(null); setCode(''); setError(null) }}>Discard setup</Button></>}</section>
}
