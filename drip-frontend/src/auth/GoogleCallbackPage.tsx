import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from './AuthProvider'

export function GoogleCallbackPage() {
  const auth = useAuth()
  // Treat URL values only as presentation hints, never as proof of authentication.
  const [outcome] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('error') === 'cancelled') return 'cancelled'
    return window.location.search || window.location.hash ? 'failed' : 'session'
  })
  useEffect(() => {
    // No provider codes, tokens or arbitrary error text belong in the frontend URL.
    window.history.replaceState(window.history.state, '', window.location.pathname)
  }, [])
  if (outcome !== 'session') return <section className="container page">
    <p className="eyebrow">Google sign-in</p>
    <h1>{outcome === 'cancelled' ? 'Sign-in cancelled' : 'Sign-in could not be completed'}</h1>
    <p role="status">{outcome === 'cancelled' ? 'This Google sign-in attempt was cancelled.' : 'This attempt could not be verified. The link may have expired, or this account may need its existing sign-in method.'}</p>
    <p>An existing session may still be active. This message does not confirm a new sign-in.</p>
    <Link className="button" to="/login">Return to sign in</Link>
    <p><Link to="/account">Check your account session</Link></p>
  </section>
  return <section className="container page">
    <p className="eyebrow">Google sign-in</p>
    <h1>{auth.loading ? 'Checking your session' : auth.user && !auth.error ? 'You’re signed in' : 'Session could not be restored'}</h1>
    {auth.loading ? <p role="status">Checking the secure session created by the server…</p>
      : auth.user && !auth.error ? <><p role="status">Your account session is available. No sign-in tokens were read from this URL.</p><Link className="button" to="/account">Continue to your account</Link></>
      : <><p role="alert">We could not confirm an active session. Check that cookies are allowed, then return to sign in. No sign-in attempt will be retried automatically.</p><Link className="button" to="/login">Return to sign in</Link></>}
  </section>
}
