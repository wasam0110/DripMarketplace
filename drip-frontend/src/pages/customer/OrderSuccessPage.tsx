import { useParams, Link } from 'react-router-dom'
import { CheckCircle2, ArrowUpRight } from 'lucide-react'
import { useOrder } from '@/hooks/useOrders'
import { pkr } from '@/utils/currency'

export default function OrderSuccessPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const { data: order } = useOrder(orderId)

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-20 flex flex-col items-center gap-8 text-center">
      <CheckCircle2 size={48} className="text-success" />
      <div>
        <h1 className="text-3xl font-bold">Order placed.</h1>
        {order && (
          <p className="text-muted text-sm mt-2">
            Order <span className="text-white font-mono">#{order.order_number}</span>
          </p>
        )}
        {order?.payment_method === 'cod' && (
          <p className="text-warning text-xs mt-3">
            COD order — our team will call to confirm within 24 hours.
          </p>
        )}
      </div>
      {order && (
        <div className="w-full panel flex flex-col gap-3 text-left">
          {order.items.map(i => (
            <div key={i.id} className="flex justify-between text-sm">
              <span className="text-muted">{i.product_name} × {i.quantity}</span>
              <span className="font-bold">{pkr(i.subtotal)}</span>
            </div>
          ))}
          <div className="border-t border-border pt-3 flex justify-between font-bold">
            <span>Total</span><span>{pkr(order.total)}</span>
          </div>
        </div>
      )}
      <div className="flex gap-3">
        <Link to="/account/orders" className="btn-primary">View orders <ArrowUpRight size={15} /></Link>
        <Link to="/shop" className="btn-outline">Keep shopping</Link>
      </div>
    </div>
  )
}
