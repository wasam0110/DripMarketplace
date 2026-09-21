import type { ProductVariant } from '@/types/product'
import { Badge } from '@/components/ui/Badge'
import { pkr } from '@/utils/currency'

export function VariantMatrix({ variants }: { variants: ProductVariant[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            {['SKU', 'Colour', 'Size', 'Price', 'Stock', 'Status'].map(h => (
              <th key={h} className="px-3 py-2 text-[10px] font-bold tracking-widest text-muted uppercase">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {variants.map(v => (
            <tr key={v.id} className="hover:bg-surface/50">
              <td className="px-3 py-2 font-mono text-xs text-muted">{v.sku}</td>
              <td className="px-3 py-2 text-xs">{v.colour}</td>
              <td className="px-3 py-2 text-xs">{v.size_value}</td>
              <td className="px-3 py-2 font-bold text-xs">{pkr(v.effective_price)}</td>
              <td className="px-3 py-2 text-xs">{v.stock}</td>
              <td className="px-3 py-2">
                <Badge label={v.stock > 0 ? 'IN STOCK' : 'OUT'} variant={v.stock > 0 ? 'success' : 'danger'} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
