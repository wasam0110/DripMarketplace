import { Badge } from '@/components/ui/Badge'
import { pkr } from '@/utils/currency'

const STATUS_VARIANT: Record<string, 'success'|'warning'|'danger'|'muted'> = {
  delivered: 'success', shipped: 'success',
  processing: 'warning', pending_cod_verification: 'warning',
  cancelled: 'danger', returned: 'danger',
}

interface SellerOrder {
  id: string; order_number: string; status: string
  customer_name: string; total: number; created_at: string
}

export function OrderTable({ orders, loading }: { orders: SellerOrder[]; loading?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            {['Order', 'Customer', 'Total', 'Status', 'Date'].map(h => (
              <th key={h} className="px-4 py-3 text-[10px] font-bold tracking-widest text-muted uppercase">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {orders.map(o => (
            <tr key={o.id} className="hover:bg-surface/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-accent">#{o.order_number}</td>
              <td className="px-4 py-3 text-sm">{o.customer_name}</td>
              <td className="px-4 py-3 font-bold">{pkr(o.total)}</td>
              <td className="px-4 py-3">
                <Badge label={o.status.replace(/_/g, ' ').toUpperCase()} variant={STATUS_VARIANT[o.status] ?? 'muted'} />
              </td>
              <td className="px-4 py-3 text-xs text-muted">{new Date(o.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
          {!loading && orders.length === 0 && (
            <tr><td colSpan={5} className="px-4 py-12 text-center text-muted text-sm">No orders yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
