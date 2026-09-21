import { Button } from '@/components/ui/Button'
import { pkr } from '@/utils/currency'
import { adminApi } from '@/api/admin.api'
import { toast } from '@/components/ui/Toast'

interface CODOrder { id: string; order_number: string; customer_name: string; phone: string; total: number; created_at: string }

export function CODQueue({ orders, onRefresh }: { orders: CODOrder[]; onRefresh: () => void }) {
  async function verify(id: string) {
    try { await adminApi.verifyCod(id, {}); toast.success('Order verified'); onRefresh() }
    catch { toast.error('Failed to verify') }
  }
  async function cancel(id: string) {
    try { await adminApi.verifyCod(id, { action: 'cancel' }); toast.success('Order cancelled'); onRefresh() }
    catch { toast.error('Failed to cancel') }
  }

  if (!orders.length) return <p className="text-muted text-sm py-8 text-center">No COD orders pending verification.</p>

  return (
    <div className="flex flex-col divide-y divide-border">
      {orders.map(o => (
        <div key={o.id} className="py-4 flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-sm text-accent">#{o.order_number}</p>
            <p className="text-sm font-bold">{o.customer_name}</p>
            <p className="text-xs text-muted">{o.phone}</p>
          </div>
          <div className="text-right">
            <p className="font-bold">{pkr(o.total)}</p>
            <p className="text-[10px] text-muted">{new Date(o.created_at).toLocaleDateString()}</p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button size="sm" onClick={() => verify(o.id)}>Verify</Button>
            <Button size="sm" variant="outline" onClick={() => cancel(o.id)}>Cancel</Button>
          </div>
        </div>
      ))}
    </div>
  )
}
