import { Star, CheckCircle2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/Skeleton'
import type { Review } from '@/types/product'

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(n => (
        <Star key={n} size={12} fill={n <= rating ? 'currentColor' : 'none'}
          className={n <= rating ? 'text-accent' : 'text-border'} />
      ))}
    </div>
  )
}

interface Props { reviews: Review[]; loading?: boolean; avgRating?: number; total?: number }

export function ReviewList({ reviews, loading, avgRating, total }: Props) {
  if (loading) return (
    <div className="flex flex-col gap-6">
      {[1,2,3].map(i => <div key={i} className="flex flex-col gap-2"><Skeleton className="h-3 w-32" /><Skeleton className="h-12 w-full" /></div>)}
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      {avgRating != null && total != null && total > 0 && (
        <div className="flex items-center gap-4 pb-6 border-b border-border">
          <span className="text-4xl font-bold">{avgRating.toFixed(1)}</span>
          <div>
            <Stars rating={Math.round(avgRating)} />
            <p className="text-xs text-muted mt-1">{total} reviews</p>
          </div>
        </div>
      )}

      {reviews.length === 0 ? (
        <p className="text-muted text-sm">No reviews yet. Be the first.</p>
      ) : reviews.map(r => (
        <div key={r.id} className="flex flex-col gap-2 pb-6 border-b border-border last:border-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Stars rating={r.rating} />
              {r.is_verified_purchase && (
                <span className="flex items-center gap-1 text-[10px] text-success">
                  <CheckCircle2 size={10} /> Verified purchase
                </span>
              )}
            </div>
            <span className="text-[10px] text-muted">{new Date(r.created_at).toLocaleDateString()}</span>
          </div>
          {r.title && <p className="text-sm font-bold">{r.title}</p>}
          {r.body  && <p className="text-sm text-muted leading-relaxed">{r.body}</p>}
          <p className="text-[10px] text-muted">{r.user.first_name || 'Customer'}</p>
        </div>
      ))}
    </div>
  )
}
