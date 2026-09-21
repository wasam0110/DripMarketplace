import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { ShoppingBag, ArrowUpRight, MessageCircle } from 'lucide-react'
import { ProductGallery } from '@/components/product/ProductGallery'
import { SizeSelector } from '@/components/product/SizeSelector'
import { ColourSelector } from '@/components/product/ColourSelector'
import { ReviewList } from '@/components/product/ReviewList'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { useProductBySlug, useProductReviews } from '@/hooks/useProducts'
import { useCartStore } from '@/store/cartStore'
import { toast } from '@/components/ui/Toast'
import { pkr } from '@/utils/currency'
import { whatsappLink } from '@/utils/whatsapp'

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: product, isLoading } = useProductBySlug(slug)
  const { data: reviewData } = useProductReviews(product?.id)
  const addItem  = useCartStore(s => s.addItem)
  const [selectedVariantId, setSelectedVariantId] = useState<string>()

  if (isLoading) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 grid sm:grid-cols-2 gap-12">
      <Skeleton className="aspect-[3/4] w-full" />
      <div className="flex flex-col gap-4"><Skeleton className="h-8 w-2/3" /><Skeleton className="h-5 w-1/4" /><Skeleton className="h-32 w-full" /></div>
    </div>
  )
  if (!product) return <div className="max-w-7xl mx-auto px-4 py-20 text-center text-muted">Product not found.</div>

  const variant = product.variants.find(v => v.id === selectedVariantId) ?? product.variants[0]

  function handleAddToCart() {
    if (!variant) return
    addItem(variant, product, 1)
    toast.success(`${product.name} added to bag`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col gap-16">
      <div className="grid sm:grid-cols-2 gap-10 lg:gap-20">
        {/* Gallery */}
        <ProductGallery images={product.images} name={product.name} />

        {/* Info */}
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-2">
              {product.seller.brand_name}
            </p>
            <h1 className="text-3xl font-bold leading-tight">{product.name}</h1>
            <div className="flex items-center gap-3 mt-3">
              <span className="text-2xl font-bold">{pkr(variant?.effective_price ?? (product.sale_price ?? product.price))}</span>
              {product.sale_price && product.sale_price < product.price && (
                <span className="text-muted line-through text-lg">{pkr(product.price)}</span>
              )}
            </div>
            {product.avg_rating > 0 && (
              <p className="text-xs text-muted mt-1">★ {product.avg_rating.toFixed(1)} ({product.review_count} reviews)</p>
            )}
          </div>

          <ColourSelector variants={product.variants} selected={selectedVariantId} onChange={setSelectedVariantId} />
          <SizeSelector   variants={product.variants} selected={selectedVariantId} onChange={setSelectedVariantId} />

          <div className="flex flex-col gap-3">
            <Button onClick={handleAddToCart} disabled={!product.has_stock} className="w-full justify-center">
              <ShoppingBag size={16} />
              {product.has_stock ? 'Add to bag' : 'Sold out'}
            </Button>
            {product.seller.brand_name && (
              <a href={whatsappLink('', `Hi! I'm interested in ${product.name}`)}
                className="btn-outline w-full justify-center text-whatsapp border-whatsapp/30 hover:border-whatsapp">
                <MessageCircle size={15} /> Ask the brand
              </a>
            )}
          </div>

          {product.description && (
            <div className="border-t border-border pt-6">
              <p className="text-sm text-muted leading-relaxed">{product.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Reviews */}
      <div className="border-t border-border pt-10 flex flex-col gap-6">
        <h2 className="text-xl font-bold">Reviews</h2>
        <ReviewList
          reviews={reviewData?.data ?? []}
          avgRating={(reviewData as any)?.avg_rating}
          total={reviewData?.total}
        />
      </div>
    </div>
  )
}
