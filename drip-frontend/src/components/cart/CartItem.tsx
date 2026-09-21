import { X, Minus, Plus } from 'lucide-react'
import { useCartStore } from '@/store/cartStore'
import { pkr } from '@/utils/currency'
import type { CartItem as CartItemType } from '@/types/order'

export function CartItem({ item }: { item: CartItemType }) {
  const { removeItem, updateQty } = useCartStore()
  return (
    <div className="py-4 flex gap-3">
      <div className="w-16 h-20 bg-card shrink-0 overflow-hidden">
        {item.image_url && <img src={item.image_url} alt={item.product_name} className="w-full h-full object-cover" />}
      </div>
      <div className="flex-1 flex flex-col gap-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.product_name}</p>
        <p className="text-[10px] text-muted">{item.colour} / {item.size_value}</p>
        <p className="text-sm font-bold">{pkr(item.unit_price)}</p>
        <div className="flex items-center gap-2 mt-1">
          <button onClick={() => updateQty(item.variant_id, item.quantity - 1)} className="w-6 h-6 border border-border flex items-center justify-center text-muted hover:text-white hover:border-white transition-colors">
            <Minus size={11} />
          </button>
          <span className="text-sm w-4 text-center">{item.quantity}</span>
          <button onClick={() => updateQty(item.variant_id, item.quantity + 1)} className="w-6 h-6 border border-border flex items-center justify-center text-muted hover:text-white hover:border-white transition-colors">
            <Plus size={11} />
          </button>
        </div>
      </div>
      <button onClick={() => removeItem(item.variant_id)} className="text-muted hover:text-white shrink-0">
        <X size={15} />
      </button>
    </div>
  )
}
