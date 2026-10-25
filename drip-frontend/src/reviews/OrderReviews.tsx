import { useState } from 'react'
import { Button } from '../components/ui'
import { isOrderId, type OrderDetail } from '../orders/api'
import { ReviewForm } from './ProductReviews'

/** Entry points come only from an authenticated order read, never guest access. */
export function OrderReviews({ order }: { order: OrderDetail }) {
  const [selected, setSelected] = useState<string[]>([])
  const products = order.items.filter((item, index, items) =>
    isOrderId(item.product_id) && items.findIndex((candidate) => candidate.product_id === item.product_id) === index)
  if (!['delivered', 'completed'].includes(order.status) || !products.length) return null
  return <section className="order-request" aria-labelledby="order-reviews-title">
    <h2 id="order-reviews-title">Review your pieces</h2>
    <p>Choose a piece from this order. You can review each product once per account, even if you bought multiple sizes.</p>
    <div className="option-row">{products.filter((item) => !selected.includes(item.product_id)).map((item) =>
      <Button className="button-secondary" key={item.product_id} onClick={() => setSelected((values) => [...values, item.product_id])}>Review {item.product_name}</Button>)}</div>
    {products.filter((item) => selected.includes(item.product_id)).map((item) => <div className="order-review-piece" key={item.product_id}>
      <h3>{item.product_name}</h3><ReviewForm productId={item.product_id} orderId={order.id} />
    </div>)}
  </section>
}
