import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useSellerProducts } from '@/hooks/useSeller'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { ProductForm } from '@/components/seller/ProductForm'
import { pkr } from '@/utils/currency'

export default function SellerProductsPage() {
  const [addOpen, setAddOpen] = useState(false)
  const { data, isLoading, refetch } = useSellerProducts()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Products</h1>
        <Button icon={<Plus size={15} />} onClick={() => setAddOpen(true)}>Add product</Button>
      </div>

      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {['Product', 'Price', 'Status', 'Created'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-[10px] font-bold tracking-widest text-muted uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && <tr><td colSpan={4} className="px-4 py-8 text-center text-muted text-sm">Loading…</td></tr>}
            {data?.data.map(p => (
              <tr key={p.id} className="hover:bg-surface/50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    {p.primary_image && <img src={p.primary_image} alt="" className="w-10 h-12 object-cover bg-card" />}
                    <div>
                      <p className="font-medium">{p.name}</p>
                      <p className="text-xs text-muted">{p.seller.brand_name}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 font-bold">{pkr(p.sale_price ?? p.price)}</td>
                <td className="px-4 py-3">
                  <Badge label={p.is_published ? 'LIVE' : 'DRAFT'} variant={p.is_published ? 'success' : 'muted'} />
                </td>
                <td className="px-4 py-3 text-xs text-muted">—</td>
              </tr>
            ))}
            {!isLoading && !data?.data.length && (
              <tr><td colSpan={4} className="px-4 py-12 text-center text-muted text-sm">No products yet. Add your first product.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add product">
        <ProductForm onSuccess={() => { setAddOpen(false); refetch() }} />
      </Modal>
    </div>
  )
}
