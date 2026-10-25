import { useState } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'
import type { Product } from '../api/types'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { useResource } from '../hooks/useResource'
import { useSaved } from '../saved/SavedProvider'
import { ProductCard } from './Storefront'
import { AccountWishlist } from '../saved/AccountWishlist'

function SavedPiece({ id }: { id: string }) {
  const saved = useSaved()
  const { data, error, loading, retry } = useResource<Product>(`/products/${encodeURIComponent(id)}`)
  const unavailable = error instanceof ApiError && [404, 410].includes(error.status)
  if (!loading && !error && data && typeof data.id === 'string' && data.id.toLowerCase() === id && typeof data.name === 'string' && typeof data.price === 'string') return <ProductCard product={data} />
  return <article className="saved-placeholder">
    {loading ? <p role="status">Loading saved piece…</p> : <>
      <h2>{unavailable ? 'This piece is no longer available.' : 'This piece could not be loaded.'}</h2>
      <p>Your saved reference is still here; no price or stock has been assumed.</p>
      {!unavailable && <><ErrorNotice error={error || new Error('The product response was incomplete.')} /><Button className="button-secondary" onClick={retry}>Retry this piece</Button></>}
    </>}
    <Button className="button-secondary" disabled={Boolean(saved.error)} onClick={() => saved.set(id, false)}>Remove saved reference</Button>
  </article>
}
export function SavedPage() {
  const saved = useSaved()
  const [requestedPage, setPage] = useState(1)
  const [confirmClear, setConfirmClear] = useState(false)
  const totalPages = Math.max(1, Math.ceil(saved.ids.length / 12))
  const page = Math.min(requestedPage, totalPages)
  return <section className="container page saved-page">
    <p className="eyebrow">A collection of possibilities</p><h1>Saved pieces</h1>
    <p className="lead">Keep the pieces you want to come back to.</p>
    <AccountWishlist />
    <h2>Device saves</h2>
    <p className="notice">Saved only in this browser, not synced to your account. Anyone using this browser can see this list, even after sign-out. Saving does not reserve stock or lock a price.</p>
    {!saved.ready && <p role="status">Loading your saved list…</p>}
    {Boolean(saved.error) && <Button className="button-secondary" onClick={saved.reload}>Retry saved storage</Button>}
    {saved.ready && !saved.error && (!saved.ids.length ? <EmptyState title="Make room for your next favourite."><Link className="button" to="/clothing">Explore clothing</Link></EmptyState> : <>
      <p className="saved-count">{saved.ids.length} saved {saved.ids.length === 1 ? 'piece' : 'pieces'}</p>
      <div className="product-grid">{saved.ids.slice((page - 1) * 12, page * 12).map((id) => <SavedPiece key={id} id={id} />)}</div>
      {totalPages > 1 && <nav className="option-row" aria-label="Saved pieces pages"><Button className="button-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous pieces</Button>
        <span role="status">Page {page} of {totalPages}</span><Button className="button-secondary" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Next saved pieces</Button></nav>}
    </>)}
    {saved.ready && (saved.ids.length > 0 || Boolean(saved.error)) && <div className="saved-clear">
      {!confirmClear ? <Button className="button-secondary" onClick={() => setConfirmClear(true)}>Clear saved pieces</Button> : <>
        <p>Remove every saved reference from this browser? This cannot be undone and will not change your bag or orders.</p>
        <div className="option-row"><Button onClick={() => { if (saved.clear()) { setConfirmClear(false); setPage(1) } }}>Yes, clear this list</Button>
          <Button className="button-secondary" onClick={() => setConfirmClear(false)}>Keep my saved pieces</Button></div>
      </>}
    </div>}
  </section>
}
