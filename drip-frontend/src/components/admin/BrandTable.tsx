import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { pkr } from '@/utils/currency'
import { adminApi } from '@/api/admin.api'
import { toast } from '@/components/ui/Toast'

const STATUS_VARIANT: Record<string, 'success'|'warning'|'danger'|'muted'> = {
  active: 'success', pending: 'warning', suspended: 'danger',
}

interface Brand { id: string; brand_name: string; status: string; product_count: number; total_gmv: number }

export function BrandTable({ brands, onRefresh }: { brands: Brand[]; onRefresh: () => void }) {
  async function approve(id: string) {
    try { await adminApi.approveSeller(id); toast.success('Seller approved'); onRefresh() }
    catch { toast.error('Failed to approve') }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            {['Brand', 'Products', 'GMV', 'Status', 'Actions'].map(h => (
              <th key={h} className="px-4 py-3 text-left text-[10px] font-bold tracking-widest text-muted uppercase">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {brands.map(b => (
            <tr key={b.id} className="hover:bg-surface/50">
              <td className="px-4 py-3 font-bold">{b.brand_name}</td>
              <td className="px-4 py-3 text-muted">{b.product_count}</td>
              <td className="px-4 py-3 font-bold">{pkr(b.total_gmv)}</td>
              <td className="px-4 py-3">
                <Badge label={b.status.toUpperCase()} variant={STATUS_VARIANT[b.status] ?? 'muted'} />
              </td>
              <td className="px-4 py-3">
                {b.status === 'pending' && (
                  <Button size="sm" variant="outline" onClick={() => approve(b.id)}>Approve</Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
