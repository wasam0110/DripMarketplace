import { ProductCard } from './ProductCard'
import { ProductCardSkeleton } from '@/components/ui/Skeleton'
import type { ProductListItem } from '@/types/product'

interface Props {
  products:  ProductListItem[]
  loading?:  boolean
  onLoadMore?: () => void
  hasMore?:  boolean
}

export function ProductGrid({ products, loading, onLoadMore, hasMore }: Props) {
  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
        {products.map(p => <ProductCard key={p.id} product={p} />)}
        {loading && Array.from({ length: 8 }).map((_, i) => <ProductCardSkeleton key={i} />)}
      </div>

      {hasMore && !loading && (
        <div className="mt-12 flex justify-center">
          <button onClick={onLoadMore} className="btn-outline">Load more</button>
        </div>
      )}

      {!loading && products.length === 0 && (
        <div className="py-24 text-center">
          <p className="text-muted text-sm">No products match your filters.</p>
        </div>
      )}
    </div>
  )
}
