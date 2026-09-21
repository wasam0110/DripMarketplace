import type { ProductVariant } from '@/types/product'

interface Props {
  variants:  ProductVariant[]
  selected?: string
  onChange:  (variantId: string) => void
}

export function ColourSelector({ variants, selected, onChange }: Props) {
  const unique = [...new Map(variants.map(v => [v.colour, v])).values()]
  if (unique.length <= 1) return null

  return (
    <div>
      <p className="text-[10px] font-bold tracking-widest text-muted mb-2 uppercase">
        Colour — <span className="normal-case">{variants.find(v => v.id === selected)?.colour}</span>
      </p>
      <div className="flex gap-2">
        {unique.map(v => (
          <button key={v.id} onClick={() => onChange(v.id)}
            className={`w-6 h-6 border-2 transition-all ${selected === v.id ? 'border-accent scale-110' : 'border-transparent hover:border-muted'}`}
            style={{ background: v.colour.toLowerCase() }}
            title={v.colour}
            aria-label={v.colour}
          />
        ))}
      </div>
    </div>
  )
}
