import type { ProductVariant } from '@/types/product'

interface Props {
  variants:  ProductVariant[]
  selected?: string
  onChange:  (variantId: string) => void
}

export function SizeSelector({ variants, selected, onChange }: Props) {
  const unique = [...new Map(variants.map(v => [v.size_value, v])).values()]
  if (unique.length <= 1 && unique[0]?.size_value === 'One Size') return null

  return (
    <div>
      <p className="text-[10px] font-bold tracking-widest text-muted mb-2 uppercase">Size</p>
      <div className="flex flex-wrap gap-2">
        {unique.map(v => {
          const inStock = v.stock > 0
          return (
            <button key={v.id} onClick={() => inStock && onChange(v.id)} disabled={!inStock}
              className={`min-w-[40px] px-3 py-2 text-xs font-bold border transition-colors
                ${selected === v.id ? 'border-accent text-accent' : 'border-border text-muted hover:border-white hover:text-white'}
                ${!inStock ? 'opacity-30 cursor-not-allowed line-through' : ''}`}>
              {v.size_value}
            </button>
          )
        })}
      </div>
    </div>
  )
}
