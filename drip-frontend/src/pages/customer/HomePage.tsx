import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { useProducts } from '@/hooks/useProducts'
import { ProductCard } from '@/components/product/ProductCard'
import { ProductCardSkeleton } from '@/components/ui/Skeleton'

const BRANDS = ['VOID FORM','NO SIGNAL','AFTERDARK','COMMON GROUND','NIGHT SHIFT','RITUAL DEPT.']

export default function HomePage() {
  const { data, isLoading } = useProducts({ sort: 'newest', limit: 8 })
  const products = data?.pages.flatMap(p => p.data) ?? []

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-32 flex flex-col sm:flex-row items-start justify-between gap-12">
        <div className="flex flex-col gap-6 max-w-lg">
          <p className="text-[10px] font-mono font-bold tracking-widest text-muted">NEW COLLECTION / 2026</p>
          <h1 className="text-5xl sm:text-7xl font-bold leading-[0.9] tracking-tight">
            Wear what's<br /><span className="text-accent">next.</span>
          </h1>
          <p className="text-muted text-base max-w-sm leading-relaxed">
            Discover independent fashion brands from across Pakistan, curated in one place.
          </p>
          <div className="flex gap-3">
            <Link to="/shop" className="btn-primary">Shop now <ArrowUpRight size={16} /></Link>
            <Link to="/sell" className="btn-outline">Sell on DRIP</Link>
          </div>
        </div>
        <div className="hidden sm:flex items-center justify-center w-80 h-80 border border-border relative">
          <div className="absolute inset-4 border border-border/50" />
          <span className="font-mono font-bold text-7xl text-border select-none">DRIP</span>
          <span className="absolute bottom-6 right-6 font-mono text-[10px] text-muted">EST. 2026</span>
        </div>
      </section>

      {/* Brand rail */}
      <section className="border-t border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col gap-4">
          <p className="text-[10px] font-mono font-bold tracking-widest text-muted">THE MALL — {BRANDS.length} INDEPENDENT LABELS</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-0 divide-x divide-border border-x border-border">
            {BRANDS.map((b, i) => (
              <Link key={b} to={`/shop?brand=${encodeURIComponent(b)}`}
                className="px-4 py-5 text-xs font-bold tracking-widest hover:bg-surface transition-colors flex flex-col gap-1">
                <span className="text-muted font-mono text-[10px]">0{i + 1}</span>
                {b}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* New arrivals */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 flex flex-col gap-8">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-1">CURATED FOR YOU</p>
            <h2 className="text-3xl font-bold">New arrivals</h2>
          </div>
          <Link to="/shop" className="text-xs text-muted hover:text-accent transition-colors flex items-center gap-1">
            View all <ArrowUpRight size={13} />
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
          {isLoading ? Array.from({ length: 8 }).map((_, i) => <ProductCardSkeleton key={i} />) : products.slice(0, 8).map(p => <ProductCard key={p.id} product={p} />)}
        </div>
      </section>

      {/* Sell banner */}
      <section className="border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 flex flex-col sm:flex-row items-start justify-between gap-8">
          <div className="flex flex-col gap-3">
            <p className="text-[10px] font-mono font-bold tracking-widest text-muted">FOR THE INDEPENDENT</p>
            <h2 className="text-4xl font-bold leading-tight">Your label<br />belongs here.</h2>
          </div>
          <div className="flex flex-col gap-4 max-w-sm">
            <p className="text-muted text-sm leading-relaxed">
              Get your pieces in front of people who get it. 50 slots, 85% of every sale, zero gatekeeping.
            </p>
            <Link to="/sell" className="btn-outline self-start">Start selling <ArrowUpRight size={15} /></Link>
          </div>
        </div>
      </section>
    </div>
  )
}
