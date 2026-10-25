import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { request } from '../api/client'
import { AccountGate, useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { validateAvatarDimensions } from '../account/avatar'
import { Button, ErrorNotice, Field } from '../components/ui'
import { isOrderId, useOrderRead } from '../orders/api'
import { confirmPhotoChange, validatePhotoFile, validateReviewPhotos, type ReviewPhotos } from './photos'

export function ReviewPhotosPage() {
  const { id = '' } = useParams()
  if (!isOrderId(id)) return <section className="container page"><h1>Review unavailable</h1><Link to="/account/reviews">Your reviews</Link></section>
  return <AccountGate title="Review photos">{(owner) => <PhotoManager key={`${owner}:${id}`} owner={owner} id={id} />}</AccountGate>
}
function PhotoManager({ owner, id }: { owner: string; id: string }) {
  const path = `/me/reviews/${id}/images`
  const validate = useCallback((value: ReviewPhotos) => validateReviewPhotos(value, owner, id), [owner, id])
  const resource = useOrderRead(path, true, validate)
  const write = useAccountWrite()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const ticket = useRef(0)
  useEffect(() => () => { ticket.current++ }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  function discard() { ticket.current++; setFile(null); setPreview(null); setChecking(false); setError(null) }
  const mutable = resource.data && ['pending', 'approved'].includes(resource.data.status)
  const disabled = write.busy || write.blocked || resource.loading || !mutable
  async function choose(candidate?: File) {
    if (!candidate || disabled) return
    const current = ++ticket.current
    setFile(null); setPreview(null); setError(null); setChecking(true); setDeleting(null)
    try {
      validatePhotoFile(candidate)
      const bitmap = await createImageBitmap(candidate)
      try { validateAvatarDimensions(bitmap.width, bitmap.height) } finally { bitmap.close() }
      if (current === ticket.current) { setFile(candidate); setPreview(URL.createObjectURL(candidate)) }
    } catch (reason) { if (current === ticket.current) setError(reason instanceof Error ? reason : new Error('Image could not be decoded.')) }
    finally { if (current === ticket.current) setChecking(false) }
  }
  function refresh() { discard(); setDeleting(null); resource.retry() }
  function save(remove?: string) {
    const before = resource.data
    if (!before || disabled || checking || (!remove && (!file || before.images.length >= 5))) return
    const body = new FormData()
    if (file) body.append('image', file)
    void write.run(async () => {
      const after = validate(await request<ReviewPhotos>(remove ? `${path}/${remove}` : path, {
        authenticated: true, method: remove ? 'DELETE' : 'POST', ...(remove ? {} : { body }),
      }))
      return confirmPhotoChange(before, after, remove)
    }, refresh, remove ? 'Photo removed from the review. Storage cleanup is queued; the review awaits moderation.' : 'Photo uploaded. The review now awaits moderation.')
  }
  return <>
    <p><Link to="/account/reviews">Back to your reviews</Link></p>
    <p>Up to five photos per review. JPEG, PNG or WebP, up to 5 MiB and 25 megapixels each.</p>
    <p className="notice">Photos can become public after moderation. Do not include faces, addresses or private documents you do not want to share. Adding or removing a photo returns the review to moderation.</p>
    {resource.loading && <p role="status">Loading review photos…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <>
      <p>{resource.data.images.length} of 5 photos · Review status: {resource.data.status}</p>
      {!mutable && <p>Photos on rejected or hidden reviews cannot be changed.</p>}
      {!resource.data.images.length && <p>No photos attached.</p>}
      <div className="option-row">{resource.data.images.map((image, index) => <div className="account-card" key={image.id}>
        <Photo url={image.url} number={index + 1} />
        <Button className="button-secondary" disabled={Boolean(disabled) || checking} onClick={() => { discard(); setDeleting(image.id) }}>Remove photo {index + 1}</Button>
        {deleting === image.id && <><p>Remove this photo? It will no longer appear with this review; storage cleanup runs separately.</p>
          <Button disabled={Boolean(disabled)} onClick={() => save(image.id)}>Yes, remove photo</Button>
          <Button className="button-secondary" disabled={write.busy} onClick={() => setDeleting(null)}>Keep photo</Button></>}
      </div>)}</div>
      {resource.data.images.length >= 5 ? <p>The five-photo limit has been reached.</p> : <div className="account-card auth-form">
        <Field label="Choose review photo" type="file" accept="image/jpeg,image/png,image/webp" disabled={Boolean(disabled)} onChange={(event) => { const selected = event.target.files?.[0]; event.target.value = ''; void choose(selected) }} />
        {checking && <p role="status">Checking image…</p>}{Boolean(error) && <ErrorNotice error={error} />}
        {preview && <><img src={preview} alt="Selected review photo preview" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} /><p>This local preview has not been uploaded.</p></>}
        <Button disabled={Boolean(disabled) || checking || !file} onClick={() => save()}>Upload selected review photo</Button>
        <Button className="button-secondary" disabled={write.busy || (!preview && !checking && !error)} onClick={discard}>Discard selected photo</Button>
      </div>}
    </>}
    <Button className="button-secondary" disabled={write.busy || checking || resource.loading} onClick={refresh}>Refresh review photos</Button>
    <p className="muted">Refresh discards unsaved selections. Unknown changes remain locked on this page; check server state before repeating a request.</p>
  </>
}
function Photo({ url, number }: { url: string; number: number }) {
  const [failed, setFailed] = useState(false)
  return failed ? <p>Photo {number} could not be displayed.</p> : <img src={url} alt={`Review photo ${number}`} referrerPolicy="no-referrer" width={180} height={180} style={{ objectFit: 'contain', maxWidth: '100%' }} onError={() => setFailed(true)} />
}
