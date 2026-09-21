import { Button } from '@/components/ui/Button'
import { pkr } from '@/utils/currency'
import { adminApi } from '@/api/admin.api'
import { toast } from '@/components/ui/Toast'

interface Payout { id: string; seller_name: string; amount: number; bank_name: string; account_number: string; requested_at: string }

export function PayoutQueue({ payouts, onRefresh }: { payouts: Payout[]; onRefresh: () => void }) {
  async function approve(id: string) {
    try { await adminApi.approvePayout(id, {}); toast.success('Payout approved'); onRefresh() }
    catch { toast.error('Failed to approve') }
  }

  if (!payouts.length) return <p className="text-muted text-sm py-8 text-center">No pending payouts.</p>

  return (
    <div className="flex flex-col divide-y divide-border">
      {payouts.map(p => (
        <div key={p.id} className="py-4 flex items-center justify-between gap-4">
          <div>
            <p className="font-bold text-sm">{p.seller_name}</p>
            <p className="text-xs text-muted">{p.bank_name} · {p.account_number}</p>
          </div>
          <div className="text-right">
            <p className="font-bold text-accent">{pkr(p.amount)}</p>
            <p className="text-[10px] text-muted">{new Date(p.requested_at).toLocaleDateString()}</p>
          </div>
          <Button size="sm" onClick={() => approve(p.id)}>Approve</Button>
        </div>
      ))}
    </div>
  )
}
