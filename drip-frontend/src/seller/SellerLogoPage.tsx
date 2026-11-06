import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { request } from '../api/client'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { validateAvatarDimensions, validateAvatarFile } from '../account/avatar'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { confirmSellerLogo, safeLogoUrl, validateSellerLogo, type SellerLogo } from './logo'

export function SellerLogoPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Your brand logo</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage your logo</h1>
    {error && <ErrorNotice error={new Error(error)} />}<Link className="button" to="/login">Sign in</Link>
  </section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page account-page">
    <Link className="text-link" to="/seller/profile">Back to brand profile</Link>
    <p className="eyebrow">WearHowZ · Your label</p><h1>Your brand logo</h1>
    <LogoManager key={user.id} />
  </section>
}

function LogoManager() {
  const identity = useRef<string | null>(null)
  const validate = useCallback((value: SellerLogo) => {
    const profile = validateSellerLogo(value)
    if (identity.current !== null && profile.id !== identity.current) throw new Error('The seller identity changed. Sign in again before managing this logo.')
    identity.current = profile.id
    return profile
  }, [])
  const resource = useOrderRead('/seller/me', true, validate)
  const write = useAccountWrite()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const ticket = useRef(0)
  useEffect(() => () => { ticket.current++ }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  function discard() { ticket.current++; setFile(null); setPreview(null); setChecking(false); setError(null) }
  async function choose(candidate: File | undefined) {
    if (!candidate || write.busy || write.blocked) return
    const current = ++ticket.current
    setFile(null); setPreview(null); setError(null); setChecking(true)
    try {
      validateAvatarFile(candidate)
      const bitmap = await createImageBitmap(candidate)
      try { validateAvatarDimensions(bitmap.width, bitmap.height) } finally { bitmap.close() }
      if (current !== ticket.current) return
      setPreview(URL.createObjectURL(candidate)); setFile(candidate)
    } catch (reason) {
      if (current === ticket.current) setError(reason instanceof Error && reason.message.includes('Choose') ? reason : new Error('This logo could not be decoded. Choose a valid JPEG, PNG or WebP image.'))
    } finally { if (current === ticket.current) setChecking(false) }
  }
  const disabled = write.busy || write.blocked || checking || resource.loading || !resource.data
  return <>
    <p>Choose a JPEG, PNG or WebP logo up to 2 MiB and 25 megapixels. Selection and preview stay on this device until you upload.</p>
    <p className="notice">Your logo may appear publicly with your brand. Upload only artwork you have permission to use. The server converts it to WebP and may resize it; this is not a crop editor.</p>
    {resource.loading && <p role="status">Loading saved logo…</p>}
    {Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <div className="account-card auth-form">
      <h2>{resource.data.brand_name}</h2>
      {resource.data.logo_url ? <SavedLogo key={resource.data.logo_url} url={resource.data.logo_url} /> : <p>No brand logo saved.</p>}
      <Field label="Choose brand logo" type="file" accept="image/jpeg,image/png,image/webp" disabled={write.busy || write.blocked || resource.loading} onChange={(event) => {
        const selected = event.target.files?.[0]; event.target.value = ''; void choose(selected)
      }} />
      {checking && <p role="status">Checking logo…</p>}{Boolean(error) && <ErrorNotice error={error} />}
      {preview && <><h3>Selected logo preview</h3><img src={preview} alt="Selected brand logo preview" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} /><p>This selection has not been uploaded.</p></>}
      <Button disabled={Boolean(disabled) || !file} onClick={() => {
        if (disabled || !file || !resource.data) return
        const sellerId = resource.data.id
        const current = ticket.current
        const body = new FormData(); body.append('logo', file)
        void write.run(async () => {
          const uploaded = await request<{ logo_url: string }>('/seller/logo', { authenticated: true, method: 'POST', body })
          const url = safeLogoUrl(uploaded?.logo_url)
          if (current !== ticket.current) throw new Error('The session changed before logo confirmation.')
          // A safe upload URL alone does not prove that this seller profile saved it.
          const confirmed = await request<SellerLogo>('/seller/me', { authenticated: true, cache: 'no-store' })
          return confirmSellerLogo(confirmed, sellerId, url)
        }, () => { discard(); resource.retry() }, 'Brand logo saved and confirmed.')
      }}>Upload selected logo</Button>
      <Button className="button-secondary" disabled={write.busy || (!file && !preview && !checking && !error)} onClick={discard}>Discard selected logo</Button>
      <p className="muted">Discard removes only the local selection. Upload replaces the profile’s logo reference; it does not promise deletion of old stored images. Removing a saved logo is not supported by this API.</p>
    </div>}
    <Button className="button-secondary" disabled={write.busy || resource.loading || checking} onClick={() => { discard(); resource.retry() }}>Refresh saved logo</Button>
    <p className="muted">Refresh discards local selection and reads server data. An uncertain upload remains locked on this page, even after refreshing. Do not repeat it until its outcome is resolved.</p>
  </>
}

function SavedLogo({ url }: { url: string }) {
  const [failed, setFailed] = useState(false)
  return failed ? <p>The saved logo could not be displayed.</p> : <img src={url} alt="Current brand logo" referrerPolicy="no-referrer" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} onError={() => setFailed(true)} />
}
