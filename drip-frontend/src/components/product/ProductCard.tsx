import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { pkr } from '@/utils/currency'
import type { ProductListItem } from '@/types/product'

interface Props {
  product: ProductListItem
  onQuickAdd?: () => void
}

export function ProductCard({ product: p, onQuickAdd }: Props) {
  const [liked, setLiked] = useState(false)
  const hasDiscount = p.sale_price && p.sale_price < p.price

  return (
    <article className="group flex flex-col gap-3">
      <div className="relative overflow-hidden bg-card aspect-[3/4]">
        <Link to={`/product/${p.slug}`}>
          {p.primary_image ? (
            <img src={p.primary_image} alt={p.name}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full bg-surface flex items-center justify-center text-muted text-xs font-mono">NO IMAGE</div>
          )}
        </Link>

        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-1">
          {p.badge && <Badge label={p.badge} variant={p.badge === 'SALE' ? 'danger' : 'accent'} />}
          {!p.has_stock && <Badge label="SOLD OUT" variant="muted" />}
        </div>

        {/* Wishlist */}
        <button
          onClick={() => setLiked(l => !l)}
          className="absolute top-3 right-3 w-8 h-8 bg-bg/80 flex items-center justify-center transition-colors hover:bg-bg"
          aria-label="Add to wishlist"
        >
          <Heart size={14} fill={liked ? 'currentColor' : 'none'} className={liked ? 'text-danger' : 'text-white'} />
        </button>

        {/* Quick Add */}
        {p.has_stock && onQuickAdd && (
          <button
            onClick={onQuickAdd}
            className="absolute bottom-0 inset-x-0 bg-accent text-bg text-xs font-bold tracking-widest py-2.5 flex items-center justify-center gap-2 translate-y-full group-hover:translate-y-0 transition-transform duration-200"
          >
            <Plus size={13} /> QUICK ADD
          </button>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-[10px] text-muted font-medium tracking-widest uppercase">{p.seller.brand_name}</p>
        <Link to={`/product/${p.slug}`} className="text-sm font-medium hover:text-accent transition-colors line-clamp-2">
          {p.name}
        </Link>
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm">{pkr(p.sale_price ?? p.price)}</span>
          {hasDiscount && <span className="text-muted text-xs line-through">{pkr(p.price)}</span>}
        </div>
        {p.avg_rating > 0 && (
          <p className="text-[10px] text-muted">★ {p.avg_rating.toFixed(1)} <span>({p.review_count})</span></p>
        )}
      </div>
    </article>
  )
}
