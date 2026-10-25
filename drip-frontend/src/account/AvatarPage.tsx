import { useCallback, useEffect, useRef, useState } from 'react'
import { request } from '../api/client'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { AccountGate, useAccountWrite, WriteFeedback } from './AccountDetails'
import { safeAvatarUrl, validateAvatarDimensions, validateAvatarFile, validateAvatarProfile, type AvatarProfile } from './avatar'

export function AvatarPage() {
  return <AccountGate title="Your profile photo">{(owner) => <AvatarManager key={owner} owner={owner} />}</AccountGate>
}
function AvatarManager({ owner }: { owner: string }) {
  const validate = useCallback((value: AvatarProfile) => validateAvatarProfile(value, owner), [owner])
  const resource = useOrderRead('/me', true, validate)
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
      if (current === ticket.current) setError(reason instanceof Error && reason.message.includes('Choose') ? reason : new Error('This image could not be decoded. Choose a valid JPEG, PNG or WebP image.'))
    } finally { if (current === ticket.current) setChecking(false) }
  }
  const disabled = write.busy || write.blocked || checking || resource.loading || !resource.data
  return <>
    <p>Choose a JPEG, PNG or WebP image up to 2 MiB and 25 megapixels. Previewing stays on your device; upload happens only when you confirm.</p>
    <p className="notice">Your profile photo can appear with public reviews. Upload only an image you want associated with your account. The server converts uploads to WebP; this preview is not a crop editor.</p>
    {resource.loading && <p role="status">Loading profile photo…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <div className="account-card auth-form">
      <h2>Current profile photo</h2>
      {resource.data.avatar_url ? <AvatarImage key={resource.data.avatar_url} url={resource.data.avatar_url} /> : <p>No profile photo saved.</p>}
      <Field label="Choose profile photo" type="file" accept="image/jpeg,image/png,image/webp" disabled={write.busy || write.blocked || resource.loading} onChange={(event) => {
        const selected = event.target.files?.[0]; event.target.value = ''; void choose(selected)
      }} />
      {checking && <p role="status">Checking image…</p>}{Boolean(error) && <ErrorNotice error={error} />}
      {preview && <><h2>Selected photo preview</h2><img src={preview} alt="Selected profile photo preview" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} /><p>This selection has not been uploaded.</p></>}
      <Button disabled={Boolean(disabled) || !file} onClick={() => {
        if (disabled || !file) return
        const body = new FormData(); body.append('avatar', file)
        void write.run(async () => {
          const result = await request<{ avatar_url: string }>('/me/avatar', { method: 'POST', authenticated: true, body })
          return safeAvatarUrl(result?.avatar_url)
        }, () => { discard(); resource.retry() }, 'Profile photo uploaded. Refreshing the saved photo.')
      }}>Upload selected photo</Button>
      <Button className="button-secondary" disabled={write.busy || (!file && !preview && !checking && !error)} onClick={discard}>Discard selected photo</Button>
      <p className="muted">Discard clears only your local selection. Removing an already saved photo is not supported by this screen.</p>
    </div>}
    <Button className="button-secondary" disabled={write.busy || resource.loading || checking} onClick={() => { discard(); resource.retry() }}>Refresh saved photo</Button>
    <p className="muted">Refreshing discards any unsubmitted selection. After an uncertain upload, inspect the saved photo before trying again; further uploads remain locked on this page.</p>
  </>
}
function AvatarImage({ url }: { url: string }) {
  const [failed, setFailed] = useState(false)
  return failed ? <p>The saved photo could not be displayed.</p> : <img src={url} alt="Current profile photo" referrerPolicy="no-referrer" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} onError={() => setFailed(true)} />
}
