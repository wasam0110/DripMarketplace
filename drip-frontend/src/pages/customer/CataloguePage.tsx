import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal, ChevronDown } from 'lucide-react'
import { useProducts } from '@/hooks/useProducts'
import { ProductGrid } from '@/components/product/ProductGrid'

const SORT_OPTIONS = [
  { value: 'newest',    label: 'Newest' },
  { value: 'trending',  label: 'Trending' },
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc',label: 'Price: High to Low' },
]

export default function CataloguePage() {
  const [params, setParams] = useSearchParams()
  const [filterOpen, setFilterOpen] = useState(false)
  const sort  = params.get('sort')    || 'newest'
  const q     = params.get('q')       || undefined
  const sale  = params.get('on_sale') === 'true'

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useProducts({ sort, q, on_sale: sale || undefined })
  const products = data?.pages.flatMap(p => p.data) ?? []

  function setSort(v: string) { const p = new URLSearchParams(params); p.set('sort', v); setParams(p) }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col gap-8">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div>
          <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-1">THE COLLECTION</p>
          <h1 className="text-2xl font-bold">{q ? `"${q}"` : 'All products'}</h1>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setFilterOpen(o => !o)} className="btn-ghost flex items-center gap-2 border border-border px-4 py-2 text-xs">
            <SlidersHorizontal size={14} /> Filters
          </button>
          <div className="relative">
            <select value={sort} onChange={e => setSort(e.target.value)}
              className="appearance-none bg-surface border border-border text-xs font-bold px-4 py-2 pr-8 focus:outline-none focus:border-accent cursor-pointer">
              {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted" />
          </div>
        </div>
      </div>

      <ProductGrid
        products={products}
        loading={isLoading || isFetchingNextPage}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
      />
    </div>
  )
}
