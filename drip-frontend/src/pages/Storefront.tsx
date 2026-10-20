import { Link, useParams, useSearchParams } from 'react-router'
import { useState } from 'react'
import { formatPrice, type Brand, type BrandsPage, type CataloguePage, type Product } from '../api/types'
import { Arrow, Button, EmptyState, ErrorNotice } from '../components/ui'
import { useResource } from '../hooks/useResource'

function ProductImage({ product }: { product: Product }) {
  const [failed, setFailed] = useState(false)
  return <div className="product-image">
    {product.primary_image && !failed
      ? <img src={product.primary_image} alt={product.name} loading="lazy" onError={() => setFailed(true)} />
      : <span className="image-fallback">WearHowZ<span>Image coming soon</span></span>}
    {!product.has_stock && <span className="stock-label">Currently unavailable</span>}
  </div>
}

export function ProductCard({ product }: { product: Product }) {
  return <article className="product-card">
    <Link to={`/products/${encodeURIComponent(product.id)}`}>
      <ProductImage product={product} />
      <div className="product-meta"><p className="eyebrow">{product.brand_name}</p><Arrow /></div>
      <h3>{product.name}</h3>
      <p>{formatPrice(product.sale_price ?? product.price)}
        {product.sale_price && <del>{formatPrice(product.price)}</del>}
      </p>
    </Link>
  </article>
}

function ProductGrid({ path, paginate = false }: { path: string; paginate?: boolean }) {
  const [params, setParams] = useSearchParams()
  const { data, loading, error, retry } = useResource<CataloguePage>(path)
  if (loading) return <div className="product-grid" role="status" aria-label="Loading clothing">
    {[1, 2, 3, 4].map((key) => <div className="skeleton-card" key={key}><div /><span /><span /></div>)}
  </div>
  if (error) return <div className="resource-error"><ErrorNotice error={error} /><Button onClick={retry}>Try again</Button></div>
  if (!data?.data.length) return <EmptyState title="Room for something good.">
    <p>No pieces are available in this edit yet. Try another search or come back soon.</p>
    {params.toString() && <Link className="text-link" to="/clothing">Clear filters <Arrow /></Link>}
  </EmptyState>
  return <>
    <div className="product-grid">{data.data.map((product) => <ProductCard key={product.id} product={product} />)}</div>
    {paginate && <div className="pagination">
      {params.has('cursor') && <Button className="button-secondary" onClick={() => {
        const next = new URLSearchParams(params); next.delete('cursor'); setParams(next)
      }}>Back to first page</Button>}
      {data.pagination.has_next && data.pagination.next_cursor && <Button onClick={() => {
        const next = new URLSearchParams(params); next.set('cursor', data.pagination.next_cursor!); setParams(next)
      }}>Next pieces <Arrow /></Button>}
    </div>}
  </>
}

export function HomePage() {
  return <>
    <section className="hero container" aria-labelledby="hero-title">
      <div className="hero-copy">
        <p className="eyebrow">The independent edit</p>
        <h1 id="hero-title">Good labels.<br /><em>Great finds.</em></h1>
        <p className="hero-description">Discover independent brands and pieces you’ll make your own.</p>
        <Link className="button button-ivory" to="/clothing?sort=newest">Shop new arrivals <Arrow /></Link>
        <Link className="hero-secondary" to="/brands">Explore brands <span aria-hidden="true">→</span></Link>
        <span className="hero-footnote">A different perspective. A considered wardrobe.</span>
      </div>
      <div className="hero-image">
        <img src="/assets/editorial.png" alt="Two models in relaxed neutral tailoring beside a green doorway" fetchPriority="high" />
        <span className="image-caption">Independent style, all in one place.</span>
      </div>
    </section>
    <div className="editorial-strip container"><span>Distinctive labels</span><span>Considered pieces</span><span>Your own point of view</span></div>
    <section className="container collection-section" aria-labelledby="arrivals-title">
      <div className="section-heading"><div><p className="eyebrow">Just landed</p><h2 id="arrivals-title">Fresh from the labels</h2></div>
        <Link className="text-link" to="/clothing?sort=newest">View all new arrivals <Arrow /></Link>
      </div>
      <ProductGrid path="/products?sort=newest&limit=4" />
    </section>
    <section className="brand-invitation container">
      <div><p className="eyebrow">The brand directory</p><h2>Find a label that<br /><em>feels like you.</em></h2></div>
      <div><p>Different perspectives. One considered wardrobe.<br />Get to know the people behind the pieces.</p><Link className="text-link" to="/brands">Meet the labels <Arrow /></Link></div>
    </section>
  </>
}

export function CataloguePageView() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q')?.slice(0, 200) ?? ''
  const allowedSorts = ['newest', 'price_asc', 'price_desc', 'rating', 'trending']
  const sort = allowedSorts.includes(params.get('sort') ?? '') ? params.get('sort')! : 'newest'
  const query = new URLSearchParams({ sort, limit: '20' })
  if (q) query.set('q', q)
  if (params.get('cursor')) query.set('cursor', params.get('cursor')!)
  return <section className="container page">
    <p className="eyebrow">The clothing edit</p><h1>{q ? `Your edit: “${q}”` : 'New arrivals'}</h1>
    <p className="lead">Distinct pieces from independent labels.</p>
    <div className="catalogue-toolbar">
      <form className="inline-search" onSubmit={(event) => {
        event.preventDefault()
        const value = String(new FormData(event.currentTarget).get('q') ?? '').trim()
        setParams(value ? { q: value, sort } : { sort })
      }}>
        <label className="sr-only" htmlFor="catalogue-query">Search clothing</label>
        <input key={q} id="catalogue-query" type="search" name="q" defaultValue={q} maxLength={200} placeholder="Search the clothing edit" />
        <Button type="submit" className="button-secondary">Search</Button>
      </form>
      <label className="sort-label">Sort
        <select value={sort} onChange={(event) => {
          const next = new URLSearchParams(params); next.set('sort', event.target.value); next.delete('cursor'); setParams(next)
        }}>
          <option value="newest">Newest first</option><option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option><option value="rating">Highest rated</option><option value="trending">Trending</option>
        </select>
      </label>
    </div>
    <ProductGrid path={`/products?${query}`} paginate />
  </section>
}

export function BrandsPageView() {
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number.parseInt(params.get('page') ?? '1', 10) || 1)
  const q = params.get('q')?.slice(0, 100) ?? ''
  const { data, loading, error, retry } = useResource<BrandsPage>(`/brands?${new URLSearchParams({ q, page: String(page), per_page: '24' })}`)
  return <section className="container page">
    <p className="eyebrow">In good company</p><h1>The brand directory</h1><p className="lead">Different perspectives. One considered wardrobe.</p>
    <form className="inline-search brand-search" onSubmit={(event) => {
      event.preventDefault(); setParams({ q: String(new FormData(event.currentTarget).get('q') ?? '').trim() })
    }}><label className="sr-only" htmlFor="brand-query">Find a label</label>
      <input key={q} id="brand-query" type="search" name="q" maxLength={100} defaultValue={q} placeholder="Find a label" /><Button type="submit">Search</Button>
    </form>
    {loading ? <p role="status">Finding the labels…</p> : error ? <><ErrorNotice error={error} /><Button onClick={retry}>Try again</Button></>
      : data?.data.length ? <>
        <div className="brand-grid">{data.data.map((brand) => <Link key={brand.id} className="brand-card" to={`/brands/${encodeURIComponent(brand.slug)}`}>
          <p className="eyebrow">Independent label</p><h2>{brand.brand_name}</h2><p>{brand.description}</p><span className="text-link">Explore the collection <Arrow /></span>
        </Link>)}</div>
        <div className="pagination">
          <Button disabled={page === 1} onClick={() => setParams({ q, page: String(page - 1) })}>Previous</Button>
          <span>Page {page}</span><Button disabled={page * data.pagination.per_page >= data.pagination.total} onClick={() => setParams({ q, page: String(page + 1) })}>Next</Button>
        </div>
      </> : <EmptyState title="Good company is on its way."><p>No labels match this search yet.</p></EmptyState>}
  </section>
}

export function BrandPage() {
  const { slug = '' } = useParams()
  const path = `/brands/${encodeURIComponent(slug)}`
  const { data, error, loading, retry } = useResource<Brand>(path)
  return <section className="container page">
    <Link className="text-link" to="/brands">← All labels</Link>
    {loading ? <p role="status">Loading this label…</p> : error ? <><ErrorNotice error={error} /><Button onClick={retry}>Try again</Button></>
      : data && <>
        <p className="eyebrow page-eyebrow">Independent label</p><h1>{data.brand_name}</h1><p className="lead">{data.description}</p>
        <details className="policy"><summary>Brand return policy</summary><p>{data.return_policy || 'Return policy details have not been provided by this brand.'}</p></details>
        <ProductGrid path={`${path}/products?limit=20`} />
      </>}
  </section>
}

