import { useCallback, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { sellerLabel, sellerMoney } from './sellers'
import { confirmModerationReceipt, confirmProductModeration, moderationImage, productListQuery, productModerationMarker, sameModerationReview, validateAdminProductDetail, validateAdminProducts, type AdminProductDetail, type AdminProductPage } from './products'
import './products.css'

export function AdminProductsPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Product moderation</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to moderate products</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Catalogue review</p><h1>{detail ? 'Review product' : 'Product moderation'}</h1>
    {detail ? isOrderId(id) ? <ProductReview key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This product reference is invalid.</p> : <ProductList key={user.id} />}
  </section>
}
function ProductList() {
  const [params, setParams] = useSearchParams(), seller = params.get('seller_id') ?? '', hidden = params.get('admin_hidden') ?? 'all', page = params.get('page') ?? '1'
  const [sellerDraft, setSellerDraft] = useState(seller), [hiddenDraft, setHiddenDraft] = useState(['all', 'true', 'false'].includes(hidden) ? hidden : 'all'), [formError, setFormError] = useState<unknown>(null)
  let query = '', error: unknown = null
  try { query = productListQuery(seller, hidden, page) } catch (reason) { error = reason }
  return <><form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); try { setParams(productListQuery(sellerDraft, hiddenDraft, '1')); setFormError(null) } catch (reason) { setFormError(reason) } }}>
    <Field label="Seller reference (optional)" value={sellerDraft} onChange={(event) => setSellerDraft(event.target.value)} maxLength={36} hint="Use the seller reference, or leave blank for all brands." />
    <div className="field"><label htmlFor="admin-product-hidden">Admin restriction</label><select id="admin-product-hidden" value={hiddenDraft} onChange={(event) => setHiddenDraft(event.target.value)}><option value="all">All products</option><option value="true">Hidden by admin</option><option value="false">No admin restriction</option></select></div>
    {Boolean(formError) && <ErrorNotice error={formError} />}<Button type="submit">Apply product filters</Button>
  </form>{error ? <ErrorNotice error={error} /> : <ProductResults query={query} page={Number(page)} seller={seller.trim()} hidden={hidden} navigate={(next) => setParams(productListQuery(seller, hidden, String(next)))} />}</>
}
function ProductResults({ query, page, seller, hidden, navigate }: { query: string; page: number; seller: string; hidden: string; navigate: (page: number) => void }) {
  const validate = useCallback((value: AdminProductPage) => validateAdminProducts(value, page, seller, hidden), [page, seller, hidden])
  const resource = useOrderRead(`/admin/products?${query}`, true, validate), data = resource.data
  const pages = data ? Math.max(1, Math.ceil(data.pagination.total / 25)) : 1
  return <>{resource.loading && <p role="status">Loading products…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <>
    <p role="status">Page {page} of {pages} · {data.pagination.total} products</p>
    {!data.data.length && <EmptyState title="No products on this page"><p>Change the filters or try a previous page.</p></EmptyState>}
    {data.data.map((row) => <article className="account-card" key={row.id}><h2>{row.name}</h2><p>Base price: {sellerMoney(row.price)}</p><p>{row.admin_hidden ? 'Hidden by admin' : 'No admin restriction'} · {row.is_published ? 'Seller published' : 'Seller draft'}</p><p>Seller reference: {row.seller_id}</p><Link className="text-link" to={`/admin/products/${row.id}`}>Review {row.name}</Link></article>)}
  </>}<div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous product page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= pages} onClick={() => navigate(page + 1)}>Next product page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh product list</Button></div></>
}
function ProductReview({ owner, id }: { owner: string; id: string }) {
  const path = `/admin/products/${id}`, validate = useCallback((value: AdminProductDetail) => validateAdminProductDetail(value, id), [id])
  const resource = useOrderRead(path, true, validate), write = useAccountWrite()
  const [review, setReview] = useState<AdminProductDetail | null>(null)
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(productModerationMarker(owner, id)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || pending || resource.loading || !resource.data
  function refresh() { setReview(null); resource.retry() }
  function save(before: AdminProductDetail) {
    if (disabled) return
    const hidden = !before.admin_hidden
    void write.run(async () => {
      let sent = false
      try {
        const latest = validate(await request<AdminProductDetail>(path, { authenticated: true, cache: 'no-store' }))
        if (!sameModerationReview(before, latest)) { refresh(); throw new Error('The product or seller state changed. Review the refreshed product before deciding.') }
        sessionStorage.setItem(productModerationMarker(owner, id), 'pending'); setPending(true); sent = true
        confirmModerationReceipt(await request<{ id: string; admin_hidden: boolean }>(`${path}/${hidden ? 'hide' : 'unhide'}`, { authenticated: true, method: 'POST' }), id, hidden)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The product could not be rechecked. No change was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(productModerationMarker(owner, id)); setPending(false) }
        throw reason
      }
      let saved: AdminProductDetail
      try { saved = confirmProductModeration(await request<AdminProductDetail>(path, { authenticated: true, cache: 'no-store' }), before, hidden) }
      catch { throw new Error('The moderation change could not be confirmed. Inspect the saved product before repeating it.') }
      sessionStorage.removeItem(productModerationMarker(owner, id)); setPending(false)
      return saved
    }, refresh, 'Product moderation change saved and confirmed.')
  }
  const product = resource.data
  return <><p><Link className="text-link" to="/admin/products">Back to product moderation</Link></p>{resource.loading && <p role="status">Loading product review…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A moderation change is awaiting confirmation. Inspect the saved product or contact support before another change.</p>}
    {product && <>
      <section className="account-card"><h2>{product.name}</h2><p>Product reference: {product.id}</p><p>Created {orderDate(product.created_at)}</p><dl><dt>Admin restriction</dt><dd>{product.admin_hidden ? 'Hidden by admin' : 'No admin restriction'}</dd><dt>Seller publication</dt><dd>{product.is_published ? 'Published' : 'Draft'}</dd><dt>Brand</dt><dd><Link className="text-link" to={`/admin/sellers/${product.seller_id}`}>{product.seller.brand_name}</Link></dd><dt>Seller status</dt><dd>{sellerLabel(product.seller_status)}{product.seller_deleted ? ' · Archived account' : ''}</dd><dt>Category</dt><dd>{product.category?.name ?? 'Not categorized'}</dd><dt>Base price</dt><dd>{sellerMoney(product.price)}</dd><dt>Sale price</dt><dd>{product.sale_price === null ? 'Not set' : sellerMoney(product.sale_price)}</dd></dl><p>Removing an admin restriction does not publish a draft, activate a seller, restore an archived account or guarantee stock availability.</p></section>
      <section className="account-card"><h2>Product content</h2><p className="admin-product-copy">{product.description || 'No description supplied.'}</p><dl><dt>Page title</dt><dd>{product.meta_title || 'Not supplied'}</dd><dt>Page description</dt><dd>{product.meta_description || 'Not supplied'}</dd><dt>Brand return policy</dt><dd className="admin-product-copy">{product.seller.return_policy || 'Not supplied'}</dd></dl></section>
      <section className="account-card"><h2>Product images</h2>{!product.images.length && <p>No product images supplied.</p>}<div className="admin-product-images">{[...product.images].sort((a, b) => a.sort_order - b.sort_order || a.id.localeCompare(b.id)).map((image) => <figure key={image.id}>{moderationImage(image.url) ? <img src={moderationImage(image.url)!} alt={image.alt_text || `${product.name} product image`} loading="lazy" referrerPolicy="no-referrer" /> : <p>Image URL unavailable.</p>}<figcaption>{image.is_primary ? 'Primary image' : `Image position ${image.sort_order + 1}`}</figcaption></figure>)}</div></section>
      <section className="account-card"><h2>Variants and stock</h2>{!product.variants.length && <p>No variants supplied.</p>}{product.variants.map((variant) => <article className="admin-product-variant" key={variant.id}><h3>{variant.sku}</h3><p>{variant.size_type} · {variant.size_value} · {variant.colour}</p><dl><dt>Effective variant price</dt><dd>{sellerMoney(variant.price)}</dd><dt>Physical stock</dt><dd>{variant.stock}</dd><dt>Available after reservations</dt><dd>{variant.available_stock}</dd><dt>Variant status</dt><dd>{variant.is_active ? 'Active' : 'Inactive'}</dd></dl></article>)}</section>
      <section className="account-card"><h2>Moderation decision</h2><p>This changes only the admin restriction. It does not delete the product, alter stock or change the seller’s publication choice.</p><Button disabled={disabled || review !== null} onClick={() => setReview(product)}>{product.admin_hidden ? 'Review removing restriction' : 'Review hiding product'}</Button>
        {review && <div className="admin-product-confirm"><h3>{review.admin_hidden ? 'Remove admin restriction' : 'Hide product'}: {review.name}</h3><p>{review.admin_hidden ? 'Remove only the administrative restriction. Other seller, publication and stock rules still apply.' : 'Hide this product from public shopping while preserving its content, publication choice and inventory.'}</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm product moderation</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to moderation review</Button></div></div>}
      </section>
    </>}<Button className="button-secondary" disabled={resource.loading || write.busy} onClick={refresh}>Refresh product and discard review</Button></>
}
