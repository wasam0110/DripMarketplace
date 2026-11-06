import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { request } from '../api/client'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { validateAvatarDimensions } from '../account/avatar'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { movedImageIds, validateMedia, validateProductFile, validateProductImages, type MediaProduct, type ProductImage } from './product-media'

export function ProductMedia({ sellerId, productId }: { sellerId: string; productId: string }) {
  const validate = useCallback((value: MediaProduct) => validateMedia(value, sellerId, productId), [sellerId, productId])
  const path = `/seller/products/${productId}`
  const resource = useOrderRead(path, true, validate), write = useAccountWrite()
  const [file, setFile] = useState<File | null>(null), [preview, setPreview] = useState<string | null>(null)
  const [checking, setChecking] = useState(false), [error, setError] = useState<unknown>(null)
  const [confirmation, setConfirmation] = useState<{ kind: 'delete'; id: string } | { kind: 'publish' | 'unpublish' } | null>(null)
  const ticket = useRef(0), active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false; ticket.current++ } }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  const disabled = write.busy || write.blocked || resource.loading || !resource.data || checking
  function discard() { ticket.current++; setFile(null); setPreview(null); setChecking(false); setError(null) }
  function refresh() { discard(); setConfirmation(null); resource.retry() }
  async function choose(candidate?: File) {
    if (!candidate || disabled) return
    discard(); const current = ticket.current; setChecking(true)
    try {
      validateProductFile(candidate)
      const bitmap = await createImageBitmap(candidate)
      try { validateAvatarDimensions(bitmap.width, bitmap.height) } finally { bitmap.close() }
      if (current !== ticket.current) return
      setFile(candidate); setPreview(URL.createObjectURL(candidate))
    } catch (reason) { if (current === ticket.current) setError(reason instanceof Error ? reason : new Error('The image could not be decoded.')) }
    finally { if (current === ticket.current) setChecking(false) }
  }
  // A successful mutation followed by any failed/mismatched read is uncertain,
  // including a 4xx read: never allow it to masquerade as a definite rejection.
  async function readBack(check: (value: MediaProduct) => boolean) {
    try {
      if (!active.current) throw new Error('Session changed')
      const saved = validate(await request<MediaProduct>(path, { authenticated: true, cache: 'no-store' }))
      if (!check(saved)) throw new Error('Saved state mismatch')
    } catch { throw new Error('The saved change could not be confirmed. Inspect the product before retrying.') }
  }
  function mutate(suffix: string, method: string, body: unknown, check: (value: MediaProduct) => boolean, message: string) {
    if (disabled) return
    void write.run(async () => {
      await request(`${path}${suffix}`, { authenticated: true, method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
      await readBack(check)
    }, refresh, message)
  }
  const product = resource.data
  return <>
    <p><Link className="text-link" to={`${path}/edit`}>Edit product details</Link> · <Link className="text-link" to={`${path}/options`}>Categories and variants</Link></p>
    <p>Images may appear publicly. Upload only artwork you have permission to use. Changes can affect a live listing immediately.</p>
    {resource.loading && <p role="status">Loading images and publication status…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {product && <>
      <h2>{product.name}</h2>
      <section className="account-card"><h3>Publication</h3><p role="status">Saved publication state: {product.is_published ? 'Published' : 'Draft'}</p>
        <p>Publishing requires an image, a variant and an available listing slot. The server makes the final eligibility check. Published does not guarantee storefront visibility or moderation clearance.</p>
        <Button disabled={disabled || (!product.is_published && (!product.images.length || !product.variants.length))} onClick={() => setConfirmation({ kind: product.is_published ? 'unpublish' : 'publish' })}>{product.is_published ? 'Unpublish product' : 'Publish product'}</Button>
      </section>
      <section aria-label="Product images"><h3>Saved images ({product.images.length}/6)</h3>
        {!product.images.length && <p>No product images saved.</p>}
        {product.images.map((row, index) => <article key={row.id} className="account-card">
          <h4>Image {index + 1}{row.is_primary ? ' · Primary' : ''}</h4><SavedImage image={row} />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '1rem' }}>
            <Button className="button-secondary" disabled={disabled || row.is_primary} onClick={() => mutate(`/images/${row.id}/primary`, 'PUT', undefined, (saved) => saved.images.find((image) => image.id === row.id)?.is_primary === true, 'Primary image saved and confirmed.')}>Make image {index + 1} primary</Button>
            {([-1, 1] as const).map((direction) => <Button key={direction} className="button-secondary" disabled={disabled || (direction === -1 ? index === 0 : index === product.images.length - 1)} onClick={() => {
              const ids = movedImageIds(product.images, row.id, direction)
              mutate('/images/order', 'PUT', { image_ids: ids }, (saved) => saved.images.map((image) => image.id).join(',') === ids.join(','), 'Image order saved and confirmed.')
            }}>Move image {index + 1} {direction === -1 ? 'earlier' : 'later'}</Button>)}
            <Button className="button-secondary" disabled={disabled || (product.is_published && product.images.length === 1)} onClick={() => setConfirmation({ kind: 'delete', id: row.id })}>Remove image {index + 1}</Button>
          </div>
        </article>)}
        <p className="muted">Unpublish before removing the final image. Removal confirms the product attachment is gone, not that storage cleanup has completed.</p>
      </section>
      <section className="account-card auth-form"><h3>Add a product image</h3><p>JPEG, PNG or WebP, up to 5 MiB and 25 megapixels. Upload one image at a time; at most six per product. The server converts and may resize it.</p>
        <Field label="Choose product image" type="file" accept="image/jpeg,image/png,image/webp" disabled={disabled || product.images.length >= 6} onChange={(e) => { const selected = e.target.files?.[0]; e.target.value = ''; void choose(selected) }} />
        {checking && <p role="status">Checking image…</p>}{Boolean(error) && <ErrorNotice error={error} />}
        {preview && <><img src={preview} alt="Selected product image preview" width={200} height={200} style={{ objectFit: 'contain', maxWidth: '100%' }} /><p>This selection has not been uploaded.</p></>}
        <Button disabled={disabled || !file || product.images.length >= 6} onClick={() => {
          if (disabled || !file) return
          const body = new FormData(); body.append('images', file)
          const priorIds = product.images.map((row) => row.id)
          void write.run(async () => {
            const response = await request<{ images: ProductImage[] }>(`${path}/images`, { authenticated: true, method: 'POST', body })
            const uploaded = validateProductImages(response?.images)
            if (uploaded.length !== 1 || priorIds.includes(uploaded[0].id)) throw new Error('The uploaded image could not be identified.')
            await readBack((saved) => saved.images.some((row) => row.id === uploaded[0].id && row.url === uploaded[0].url) && priorIds.every((id) => saved.images.some((row) => row.id === id)))
          }, refresh, 'Image uploaded and confirmed.')
        }}>Upload selected image</Button>
        <Button className="button-secondary" disabled={write.busy || (!file && !checking && !error)} onClick={discard}>Discard selected image</Button>
      </section>
      {confirmation && <section className="account-card" aria-label="Confirm product change"><h3>Confirm {confirmation.kind === 'delete' ? 'image removal' : confirmation.kind}</h3>
        <p>{confirmation.kind === 'delete' ? 'This removes the saved image from the product. It cannot be undone here.' : confirmation.kind === 'publish' ? 'This can make the product available to shoppers and occupy a listing slot.' : 'This removes the product from public listing and releases its listing slot; it does not cancel existing orders.'}</p>
        <Button disabled={disabled} onClick={() => {
          if (confirmation.kind === 'delete') { const id = confirmation.id; mutate(`/images/${id}`, 'DELETE', undefined, (saved) => !saved.images.some((row) => row.id === id), 'Image removal confirmed.') }
          else { const published = confirmation.kind === 'publish'; mutate(`/${confirmation.kind}`, 'POST', undefined, (saved) => saved.is_published === published, 'Publication state saved and confirmed.') }
        }}>Confirm {confirmation.kind === 'delete' ? 'image removal' : confirmation.kind}</Button>
        <Button className="button-secondary" disabled={write.busy} onClick={() => setConfirmation(null)}>Cancel change</Button>
      </section>}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={refresh}>Refresh saved media and discard selection</Button>
    <p className="muted">Uncertain changes stay locked on this mounted page, including after refresh. Do not repeat an uncertain upload or publication action until its outcome is resolved. This is not cross-tab or server-side idempotency.</p>
  </>
}
function SavedImage({ image }: { image: ProductImage }) {
  const [failed, setFailed] = useState(false)
  return failed ? <p>Image preview unavailable.</p> : <img src={image.url} alt={image.alt_text || 'Saved product image'} referrerPolicy="no-referrer" width={240} height={240} style={{ objectFit: 'contain', maxWidth: '100%' }} onError={() => setFailed(true)} />
}
