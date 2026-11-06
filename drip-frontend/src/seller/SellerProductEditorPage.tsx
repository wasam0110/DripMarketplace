import { useCallback, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { ApiError, request } from '../api/client'
import { Button, ErrorNotice, Field } from '../components/ui'
import { isOrderId, useOrderRead } from '../orders/api'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { validateSellerSummary } from './SellerStatus'
import { ProductOptions } from './ProductOptions'
import { ProductMedia } from './ProductMedia'
import { confirmProduct, creationMarker, emptyProduct, productChanges, productDraft, validateEditableProduct, type EditableProduct, type ProductChanges, type ProductDraft } from './product-editor'

export function SellerProductEditorPage({ create = false, options = false, media = false }: { create?: boolean; options?: boolean; media?: boolean }) {
  const { user, loading, error } = useAuth()
  const { id } = useParams()
  if (loading) return <section className="container page"><h1>Product editor</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage products</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  if (!create && (!id || !isOrderId(id))) return <section className="container page"><h1>Invalid product link</h1><Link to="/seller/products">Back to catalogue</Link></section>
  return <section className="container page account-page"><Link className="text-link" to="/seller/products">Back to catalogue</Link><h1>{create ? 'Create a product draft' : media ? 'Images and publishing' : options ? 'Categories and variants' : 'Edit product details'}</h1><SellerCheck key={`${user.id}:${create ? 'new' : id}:${options}:${media}`} productId={create ? undefined : id} options={options} media={media} /></section>
}
function SellerCheck({ productId, options, media }: { productId?: string; options: boolean; media: boolean }) {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <>
    {resource.loading && <p role="status">Checking seller access…</p>}
    {Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && (resource.data.status === 'active' ? media && productId ? <ProductMedia key={resource.data.id} sellerId={resource.data.id} productId={productId} /> : options && productId ? <ProductOptions key={resource.data.id} sellerId={resource.data.id} productId={productId} /> : <Editor key={resource.data.id} sellerId={resource.data.id} productId={productId} /> : <p>An active seller account is required to manage products.</p>)}
    {!resource.data && <Button disabled={resource.loading} onClick={resource.retry}>Retry seller access</Button>}
  </>
}
function Editor({ sellerId, productId }: { sellerId: string; productId?: string }) {
  return productId ? <ExistingProduct sellerId={sellerId} productId={productId} /> : <ProductWriter sellerId={sellerId} />
}
function ExistingProduct({ sellerId, productId }: { sellerId: string; productId: string }) {
  const validate = useCallback((value: EditableProduct) => validateEditableProduct(value, sellerId, productId), [sellerId, productId])
  const resource = useOrderRead(`/seller/products/${productId}`, true, validate)
  // Keep write state mounted through read refreshes, so uncertain saves stay locked.
  return <ProductWriter sellerId={sellerId} productId={productId} initial={resource.data ?? undefined} loading={resource.loading} error={resource.error} refresh={resource.retry} />
}
function ProductWriter({ sellerId, productId, initial, loading = false, error, refresh }: { sellerId: string; productId?: string; initial?: EditableProduct; loading?: boolean; error?: unknown; refresh?: () => void }) {
  const write = useAccountWrite(), navigate = useNavigate()
  const [pending, setPending] = useState(() => { if (productId) return false; try { return sessionStorage.getItem(creationMarker(sellerId)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || pending
  function save(changes: ProductChanges) {
    if (disabled) return
    void write.run(async () => {
      if (!productId) { sessionStorage.setItem(creationMarker(sellerId), 'pending'); setPending(true) }
      let result: EditableProduct
      try {
        result = await request<EditableProduct>(`/seller/products${productId ? `/${productId}` : ''}`, { authenticated: true, method: productId ? 'PUT' : 'POST', body: JSON.stringify(productId ? changes : { ...changes, is_published: false, variants: [] }) })
      } catch (reason) {
        if (!productId && reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) {
          sessionStorage.removeItem(creationMarker(sellerId)); setPending(false)
        }
        throw reason
      }
      const confirmed = confirmProduct(result, sellerId, changes, productId)
      if (!productId) sessionStorage.removeItem(creationMarker(sellerId))
      return confirmed
    }, (result) => { if (productId) refresh?.(); else navigate(`/seller/products/${result.id}/edit`, { replace: true }) }, 'Product details saved and confirmed.')
  }
  return <>
    <p>{productId ? 'Changes to a published product can affect the live listing immediately.' : 'Create an unpublished draft without variants or images. This does not publish a listing.'}</p>
    {productId && <p><Link className="text-link" to={`/seller/products/${productId}/media`}>Manage images and publishing</Link></p>}
    {productId && <p><Link className="text-link" to={`/seller/products/${productId}/options`}>Manage category and variants</Link></p>}
    <p className="muted">Only these details are changed; existing category, inventory and publishing state are preserved on edits. Avoid editing from multiple tabs: this API has no version-conflict protection.</p>
    {loading && <p role="status">Loading product…</p>}{Boolean(error) && <ErrorNotice error={error} />}
    <WriteFeedback state={write} />
    {pending && <p role="alert">A draft submission is pending confirmation in this tab. Inspect your catalogue or contact support before creating another. Reloading does not clear this safeguard; it is not server-side idempotency.</p>}
    {(!productId || initial) && !loading && <ProductForm key={initial ? JSON.stringify(initial) : 'new'} initial={initial} disabled={disabled} save={save} />}
    {refresh && <Button className="button-secondary" disabled={loading || write.busy} onClick={refresh}>Refresh saved product and discard edits</Button>}
  </>
}
function ProductForm({ initial, disabled, save }: { initial?: EditableProduct; disabled: boolean; save: (changes: ProductChanges) => void }) {
  const [draft, setDraft] = useState<ProductDraft>(() => initial ? productDraft(initial) : { ...emptyProduct })
  const [error, setError] = useState<unknown>(null)
  const edit = (key: keyof ProductDraft, value: string) => setDraft({ ...draft, [key]: value })
  return <form className="account-card auth-form order-request" onSubmit={(event) => {
    event.preventDefault(); if (disabled) return
    try { const changes = productChanges(draft, initial); if (!Object.keys(changes).length) throw new Error('Make a change before saving.'); setError(null); save(changes) } catch (reason) { setError(reason) }
  }}>
    <Field label="Product name" value={draft.name} required minLength={2} maxLength={200} disabled={disabled} onChange={(e) => edit('name', e.target.value)} />
    <div className="field"><label htmlFor="product-description">Description</label><textarea id="product-description" value={draft.description} required minLength={10} maxLength={5000} rows={6} disabled={disabled} onChange={(e) => edit('description', e.target.value)} /></div>
    <Field label="Regular price (PKR)" inputMode="numeric" value={draft.price} required disabled={disabled} onChange={(e) => edit('price', e.target.value)} hint="Whole PKR amounts from 100 to 500,000." />
    <Field label="Sale price (PKR)" inputMode="numeric" value={draft.sale_price} disabled={disabled} onChange={(e) => edit('sale_price', e.target.value)} hint="Optional; clear this field to remove a sale price." />
    <Field label="SEO title" value={draft.meta_title} maxLength={200} disabled={disabled} onChange={(e) => edit('meta_title', e.target.value)} />
    <Field label="SEO description" value={draft.meta_description} maxLength={500} disabled={disabled} onChange={(e) => edit('meta_description', e.target.value)} />
    {Boolean(error) && <ErrorNotice error={error} />}
    <Button type="submit" disabled={disabled}>{initial ? 'Save product details' : 'Create draft'}</Button>
    <Button className="button-secondary" disabled={disabled} onClick={() => { setDraft(initial ? productDraft(initial) : { ...emptyProduct }); setError(null) }}>Discard edits</Button>
  </form>
}
