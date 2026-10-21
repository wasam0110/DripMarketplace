import { useState } from 'react'
import { Link } from 'react-router'
import { formatPrice, type CartItem } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { useCart } from '../cart/CartProvider'
import { Button, EmptyState, ErrorNotice } from '../components/ui'

function BagImage({ item }: { item: CartItem }) {
  const [failed, setFailed] = useState(false)
  return <div className="bag-image" aria-hidden="true">
    {item.primary_image && !failed ? <img src={item.primary_image} alt="" onError={() => setFailed(true)} /> : <span>W</span>}
  </div>
}

export function BagPage() {
  const bag = useCart()
  const { user } = useAuth()
  const [confirmClear, setConfirmClear] = useState(false)
  const [localError, setLocalError] = useState<unknown>(null)
  const disabled = bag.loading || bag.busy || bag.needsReview
  async function change(operation: () => Promise<void>) {
    setLocalError(null)
    try { await operation() } catch (error) { setLocalError(error) }
  }
  const groups = new Map<string, CartItem[]>()
  for (const item of bag.cart?.items ?? []) groups.set(item.seller_id, [...(groups.get(item.seller_id) ?? []), item])
  return <section className="container page">
    <p className="eyebrow">Your considered edit</p><h1>Your bag</h1>
    <p className="lead">Good pieces, from independent labels.</p>
    {!user && <p className="notice">Your selections are saved on this device. Prices and delivery come from the latest quote; stock is not reserved.</p>}
    {user && bag.guest.length > 0 && <div className="notice"><p>You have guest selections on this device. Add them to this account’s bag? Matching items use the higher quantity, not the sum.</p>
      <Button disabled={disabled || Boolean(bag.storageError)} onClick={() => void change(bag.merge)}>Merge guest bag</Button></div>}
    {bag.notice && <p role="status">{bag.notice}</p>}
    {Boolean(bag.storageError) && <ErrorNotice error={bag.storageError} />}
    {Boolean(bag.error || localError) && <ErrorNotice error={bag.error || localError} />}
    {Boolean(bag.error) && <Button disabled={bag.busy || bag.loading} onClick={bag.reload}>Refresh bag</Button>}
    {bag.needsReview && <p>That update may have reached the server. Refresh and review quantities before retrying.</p>}
    {bag.loading && <p role="status">Refreshing your bag…</p>}
    <div className="bag-layout">
      <div>
        {[...groups.entries()].map(([sellerId, items]) => <section className="bag-group" key={sellerId}>
          <h2>{items[0].brand_name}</h2><p className="muted">Fulfilled by this label</p>
          {items.map((item) => <article className="bag-item" key={item.variant_id}>
            <div className="bag-piece"><BagImage item={item} /><div><Link className="text-link" to={`/products/${encodeURIComponent(item.product_id)}`}>{item.product_name}</Link>
              <p>{item.size} · {item.colour}</p><p>{formatPrice(item.unit_price)} each</p>
              {item.quantity > item.available_stock && <p className="field-error">Only {item.available_stock} available. Reduce the quantity or remove this piece.</p>}
            </div></div>
            <div className="bag-item-actions"><label>Quantity
              <select aria-label={`Quantity for ${item.product_name}, ${item.size}, ${item.colour}`} value={item.quantity} disabled={disabled}
                onChange={(event) => void change(() => bag.update(item.variant_id, Number(event.target.value)))}>
                {Array.from({ length: Math.min(100, Math.max(item.quantity, item.available_stock)) }, (_, index) => index + 1).map((qty) =>
                  <option key={qty} value={qty} disabled={qty > item.available_stock && qty !== item.quantity}>{qty}</option>)}
              </select></label><p>{formatPrice(item.subtotal)}</p>
              <Button className="button-secondary" disabled={disabled} aria-label={`Remove ${item.product_name}, ${item.size}, ${item.colour}`}
                onClick={() => void change(() => bag.update(item.variant_id, 0))}>Remove</Button>
            </div>
          </article>)}
        </section>)}
        {!user && !bag.cart && !bag.loading && bag.guest.map((item) => <article className="bag-item" key={item.variant_id}>
          <div><Link to={`/products/${encodeURIComponent(item.product_id)}`}>View saved piece</Link><p>Quantity: {item.quantity}. Price unavailable until the quote succeeds.</p></div>
          <Button disabled={disabled} onClick={() => void change(() => bag.update(item.variant_id, 0))}>Remove saved piece</Button>
        </article>)}
        {bag.cart && !bag.cart.items.length && !bag.loading && <EmptyState title="Room for something good."><Link className="text-link" to="/clothing">Explore the clothing edit</Link></EmptyState>}
        {(bag.count > 0 || (!user && Boolean(bag.storageError))) && <div className="bag-clear">
          {confirmClear ? <><p>Remove every piece from this bag?</p><Button disabled={disabled} onClick={() => void change(async () => { await bag.clear(); setConfirmClear(false) })}>Confirm clear bag</Button>
            <Button className="button-secondary" onClick={() => setConfirmClear(false)}>Cancel</Button></>
            : <Button disabled={disabled} className="button-secondary" onClick={() => setConfirmClear(true)}>Clear bag</Button>}
        </div>}
      </div>
      {bag.cart && bag.cart.items.length > 0 && <aside className="bag-summary" aria-labelledby="bag-summary-title">
        <h2 id="bag-summary-title">Your summary</h2>
        <dl><div><dt>Subtotal</dt><dd>{formatPrice(bag.cart.subtotal)}</dd></div>
          <div><dt>Delivery</dt><dd>{formatPrice(bag.cart.shipping_fee)}</dd></div>
          <div className="bag-total"><dt>Total</dt><dd>{formatPrice(bag.cart.total)}</dd></div></dl>
        <p>Each label ships separately. Prices, availability and delivery are rechecked before ordering.</p>
        {disabled ? <Button disabled>Continue to checkout</Button> : <Link className="button" to="/checkout">Continue to checkout</Link>}
        <small>Preview delivery details and payment options. Order submission and payments remain disabled.</small>
      </aside>}
    </div>
  </section>
}
