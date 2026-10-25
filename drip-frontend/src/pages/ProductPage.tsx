import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { formatPrice, type ProductDetail } from '../api/types'
import { useCart } from '../cart/CartProvider'
import { Button, ErrorNotice } from '../components/ui'
import { useResource } from '../hooks/useResource'
import { SaveButton } from '../saved/SavedProvider'
import { ProductReviews } from '../reviews/ProductReviews'

export function ProductPage() {
  const { id = '' } = useParams()
  const { data, loading, error, retry } = useResource<ProductDetail>(`/products/${encodeURIComponent(id)}`)
  return <section className="container page">
    <Link className="text-link" to="/clothing">Back to clothing</Link>
    {loading ? <p role="status">Loading this piece…</p> : error ? <><ErrorNotice error={error} /><Button onClick={retry}>Try again</Button></>
      : data && <><ProductSelection key={data.id} product={data} /><ProductReviews key={`reviews:${data.id}`} productId={data.id} /></>}
  </section>
}

function ProductSelection({ product }: { product: ProductDetail }) {
  const bag = useCart()
  const variants = product.variants.filter((variant) => variant.is_active)
  const colours = [...new Set(variants.map((variant) => variant.colour))]
  const [colour, setColour] = useState(colours[0] ?? '')
  const [variantId, setVariantId] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [error, setError] = useState<unknown>(null)
  const [added, setAdded] = useState(false)
  const images = [...product.images].sort((a, b) => Number(b.is_primary) - Number(a.is_primary) || a.sort_order - b.sort_order)
  const [imageIndex, setImageIndex] = useState(0)
  const [failedImages, setFailedImages] = useState<string[]>([])
  const image = images[imageIndex]
  const imageUrl = image?.url ?? product.primary_image
  const selected = variants.find((variant) => variant.id === variantId)
  const disabled = bag.loading || bag.busy || bag.needsReview
  return <div className="product-detail">
    <div>
      <div className="product-image">{imageUrl && !failedImages.includes(imageUrl)
        ? <img src={imageUrl} alt={image?.alt_text || product.name} onError={() => setFailedImages((values) => [...values, imageUrl])} />
        : <span className="image-fallback">WearHowZ<span>Image coming soon</span></span>}</div>
      {images.length > 1 && <div className="option-row" aria-label="Product images">{images.map((entry, index) =>
        <Button key={entry.id} className="button-secondary" aria-pressed={index === imageIndex} onClick={() => setImageIndex(index)}>Image {index + 1}</Button>)}</div>}
    </div>
    <div>
      <Link className="eyebrow" to={`/brands/${encodeURIComponent(product.seller.slug)}`}>{product.brand_name}</Link>
      <h1>{product.name}</h1>
      <SaveButton id={product.id} name={product.name} />
      <p className="lead">{formatPrice(selected?.price ?? product.sale_price ?? product.price)}</p>
      {product.review_count > 0 && <p>{product.avg_rating} / 5 · {product.review_count} reviews</p>}
      <p className="product-description">{product.description}</p>
      <fieldset className="variant-options"><legend>Colour</legend><div className="option-row">{colours.map((value) =>
        <Button key={value} className="button-secondary" aria-pressed={value === colour} onClick={() => {
          setColour(value); setVariantId(''); setQuantity(1); setAdded(false); setError(null)
        }}>{value || 'Standard'}</Button>)}</div></fieldset>
      <fieldset className="variant-options"><legend>Size — choose your fit</legend><div className="option-row">
        {variants.filter((variant) => variant.colour === colour).map((variant) =>
          <Button key={variant.id} className="button-secondary" disabled={variant.available_stock < 1}
            aria-pressed={variant.id === variantId} onClick={() => { setVariantId(variant.id); setQuantity(1); setAdded(false) }}>
            {variant.size_value}{variant.available_stock < 1 ? ' — sold out' : ''}
          </Button>)}
      </div></fieldset>
      {!variants.length && <p role="status">This piece is currently unavailable.</p>}
      <label className="quantity-field">Quantity
        <input type="number" min={1} max={Math.min(selected?.available_stock ?? 1, 100)} value={quantity}
          disabled={!selected || disabled} onChange={(event) => { setQuantity(Number(event.target.value)); setAdded(false) }} />
      </label>
      {selected && <p className="muted">{selected.available_stock} available. Stock is confirmed again at checkout.</p>}
      <Button disabled={disabled || !selected || !Number.isInteger(quantity) || quantity < 1 || quantity > Math.min(selected.available_stock, 100)}
        onClick={async () => {
          if (!selected) return
          setError(null); setAdded(false)
          try { await bag.add(product, selected, quantity); setAdded(true) } catch (reason) { setError(reason) }
        }}>{bag.busy ? 'Updating bag…' : 'Add to bag'}</Button>
      {Boolean(error) && <ErrorNotice error={error} />}
      {bag.needsReview && <p><Link to="/bag">Review your bag before another change</Link></p>}
      {added && <p role="status">Added to your bag. <Link className="text-link" to="/bag">View bag</Link></p>}
      <details className="policy"><summary>Sold and fulfilled by {product.brand_name}</summary><p>Each label fulfils its own pieces.</p></details>
      <details className="policy"><summary>Brand return policy</summary><p>{product.seller.return_policy || 'This brand has not supplied a return policy yet.'}</p></details>
    </div>
  </div>
}
