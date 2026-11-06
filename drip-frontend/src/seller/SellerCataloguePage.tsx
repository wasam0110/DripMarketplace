import { useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { validateSellerCatalogue } from './catalogue'

export function SellerCataloguePage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Your catalogue</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to view your catalogue</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page account-page"><Link className="text-link" to="/seller">Back to seller workspace</Link><p className="eyebrow">WearHowZ · Your label</p><h1>Your catalogue</h1><Catalogue key={user.id} /></section>
}

function Catalogue() {
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const resource = useOrderRead(`/seller/products?status=${filter}&page=${page}`, true, validateSellerCatalogue)
  return <>
    <p>Review your products and listing capacity. Open a product editor to manage its details, category, variants, images and publication state.</p>
    <p><Link className="text-link" to="/seller/inventory">Manage inventory and stock</Link></p>
    <div className="field"><label htmlFor="catalogue-status">Product status</label><select id="catalogue-status" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1) }}>
      <option value="all">All products</option><option value="published">Published</option><option value="draft">Draft</option>
    </select></div>
    {resource.loading && <p role="status">Loading catalogue…</p>}
    {Boolean(resource.error) && <><ErrorNotice error={resource.error} /><p>Catalogue access requires an active seller account. A failed read does not mean your catalogue is empty.</p></>}
    {resource.data && <>
      <p><Link className="button" to="/seller/products/new">Create product draft</Link></p>
      <div className="account-card"><h2>Listing capacity</h2><dl>
        <dt>Total slots</dt><dd>{resource.data.slot_info.total_slots}</dd>
        <dt>Used slots</dt><dd>{resource.data.slot_info.slots_used}</dd>
        <dt>Available slots</dt><dd>{resource.data.slot_info.slots_available}</dd>
      </dl><p className="muted">Server-reported capacity across your catalogue, not just this page or filter.</p></div>
      {!resource.data.data.length ? <EmptyState title="No products on this page"><p>Try another filter or return to the previous page.</p></EmptyState> : <div aria-label="Seller products">
        {resource.data.data.map((product) => <article className="account-card" key={product.id} style={{ overflowWrap: 'anywhere' }}>
          <h2>{product.name}</h2><p>{product.is_published ? 'Published' : 'Draft'} · {product.category ?? 'Uncategorized'}</p>
          <p><Link className="text-link" to={`/seller/products/${product.id}/edit`}>Edit {product.name}</Link></p>
          <dl><dt>Base price</dt><dd>{new Intl.NumberFormat('en-PK', { style: 'currency', currency: 'PKR' }).format(Number(product.price))}</dd>
            <dt>Recorded stock</dt><dd>{product.total_stock}</dd><dt>Images</dt><dd>{product.image_count}</dd></dl>
        </article>)}
      </div>}
      <p className="muted">Recorded stock is not a promise of available-to-buy quantity. Published status alone does not confirm storefront visibility or moderation clearance.</p>
    </>}
    <p role="status">Page {page}</p>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
      <Button className="button-secondary" disabled={resource.loading || page === 1} onClick={() => setPage(page - 1)}>Previous page</Button>
      <Button className="button-secondary" disabled={resource.loading || resource.data?.data.length !== 20} onClick={() => setPage(page + 1)}>Next page</Button>
      <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh catalogue</Button>
    </div><p className="muted">Up to 20 products per page. The API supplies no total page count; a full page may be followed by an empty one.</p>
  </>
}
