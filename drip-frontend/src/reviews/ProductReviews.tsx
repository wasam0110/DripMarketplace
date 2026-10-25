import { useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useResource } from '../hooks/useResource'
import { ReviewVote } from './ReviewVote'

interface Review {
  id: string; product_id: string; rating: number; title: string | null; body: string | null
  status: string; is_verified_purchase: boolean; created_at: string
  user: { id: string; first_name: string | null; last_name: string | null }
  helpful_count: number; unhelpful_count: number
  images: { id: string; url: string }[]
}
interface ReviewPage {
  data: Review[]; total: number; page: number; per_page: number; pages: number
  avg_rating: number | null; rating_breakdown: Record<string, number>
}

export function ReviewForm({ productId, orderId }: { productId: string; orderId?: string }) {
  const formId = useId()
  const [busy, setBusy] = useState(false)
  const locked = useRef(false)
  const [uncertain, setUncertain] = useState(false)
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState<unknown>(null)
  if (complete) return <p role="status" className="notice">Review received and awaiting moderation. It will appear publicly only after approval.</p>
  return <form className="review-form" onSubmit={async (event) => {
    event.preventDefault()
    if (locked.current || uncertain) return
    const form = event.currentTarget
    const values = new FormData(form)
    const rating = Number(values.get('rating'))
    const title = String(values.get('title') ?? '').trim()
    const body = String(values.get('body') ?? '').trim()
    if (!Number.isInteger(rating) || rating < 1 || rating > 5 || title.length > 200 || body.length > 2000) {
      setError(new Error('Choose a rating from 1 to 5 and keep the title within 200 characters and review within 2,000.')); return
    }
    locked.current = true; setBusy(true); setError(null)
    try {
      const response = await request<Review>(`/products/${encodeURIComponent(productId)}/reviews`, {
        method: 'POST', authenticated: true,
        body: JSON.stringify({ product_id: productId, rating, title: title || null, body: body || null, ...(orderId ? { order_id: orderId } : {}) }),
      })
      if (!response?.id || response.product_id !== productId || response.status !== 'pending') throw new Error('Unconfirmed review response')
      form.reset(); setComplete(true)
    } catch (failure) {
      if (!(failure instanceof ApiError) || failure.status === 0 || failure.status >= 500) {
        setUncertain(true)
        setError(new Error('We could not confirm whether your review was received. Do not submit it again; it may be awaiting moderation. Contact support before trying again.'))
      } else {
        setError(failure)
        locked.current = false
      }
    } finally { setBusy(false) }
  }}>
    <h3>Share your perspective</h3>
    <p>One review per account and piece. Reviews are moderated before publication. Do not include private contact or order details.</p>
    <p className="muted">{orderId
      ? 'This review will be linked to this order. The server checks ownership and purchase status; linking does not guarantee a verified-purchase badge.'
      : <>This form does not link an order. To review an account purchase, start from <Link to="/orders">your delivered orders</Link>.</>} Review text stays in memory until you submit; leaving this page discards it.</p>
    <fieldset disabled={busy || uncertain} className="review-fields">
      <legend className="sr-only">Your review</legend>
      <div className="field"><label htmlFor={`${formId}-rating`}>Rating</label>
        <select id={`${formId}-rating`} name="rating" required defaultValue=""><option value="" disabled>Choose a rating</option>
          {[5, 4, 3, 2, 1].map((rating) => <option key={rating} value={rating}>{rating} out of 5</option>)}
        </select>
      </div>
      <Field label="Review title (optional)" name="title" maxLength={200} />
      <div className="field"><label htmlFor={`${formId}-body`}>Your review (optional)</label>
        <textarea id={`${formId}-body`} name="body" maxLength={2000} rows={5} aria-describedby={`${formId}-limit`} />
        <small id={`${formId}-limit`}>Up to 2,000 characters.</small>
      </div>
      <Button type="submit" disabled={busy || uncertain}>{busy ? 'Submitting review…' : 'Submit review'}</Button>
    </fieldset>
    {Boolean(error) && <ErrorNotice error={error} />}
  </form>
}

export function ProductReviews({ productId }: { productId: string }) {
  const auth = useAuth()
  const [page, setPage] = useState(1)
  const { data, loading, error, retry } = useResource<ReviewPage>(`/products/${encodeURIComponent(productId)}/reviews?page=${page}&per_page=10`)
  return <section className="product-reviews" aria-labelledby="reviews-title">
    <p className="eyebrow">From the community</p><h2 id="reviews-title">Reviews of this piece</h2>
    {loading ? <p role="status">Loading reviews…</p> : error ? <><ErrorNotice error={error} /><Button onClick={retry}>Retry reviews</Button></>
      : data && <>
        <p>{data.total > 0 && data.avg_rating !== null ? `${data.avg_rating.toFixed(1)} out of 5 · ${data.total} approved reviews` : 'No approved reviews yet.'}</p>
        {data.total > 0 && <ul className="rating-breakdown" aria-label="Ratings breakdown">{[5, 4, 3, 2, 1].map((rating) =>
          <li key={rating}>{rating} stars: {data.rating_breakdown[rating] ?? 0}</li>)}</ul>}
        <p className="muted">Newest approved reviews first. Pending reviews are not shown.</p>
        <ul className="review-list">{data.data.map((review) => <li key={review.id}>
          <article><p>{review.rating} out of 5{review.is_verified_purchase ? ' · Verified purchase' : ''}</p>
            <p className="muted">{review.user.first_name || 'Shopper'} · {Number.isNaN(Date.parse(review.created_at)) ? 'Date unavailable' : new Date(review.created_at).toLocaleDateString('en-GB')}</p>
            {review.title && <h3>{review.title}</h3>}{review.body && <p className="review-body">{review.body}</p>}
            {!auth.loading && review.status === 'approved' && review.user.id && <ReviewVote
              key={`${review.id}:${auth.user?.id ?? 'guest'}`} reviewId={review.id} authorId={review.user.id}
              viewerId={auth.user?.id ?? null} helpfulCount={review.helpful_count} unhelpfulCount={review.unhelpful_count} />}
            {review.images?.length > 0 && <div className="review-images">{review.images.map((image) => /^https:\/\//i.test(image.url) && <img key={image.id} src={image.url} alt="Customer review photo" loading="lazy" referrerPolicy="no-referrer" />)}</div>}
          </article>
        </li>)}</ul>
        {page > 1 && !data.data.length && <p>No reviews on this page. Return to an earlier page.</p>}
        {(page > 1 || data.pages > 1) && <nav className="pagination" aria-label="Review pages">
          <Button disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Previous reviews</Button>
          <span>Page {page}</span><Button disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next reviews</Button>
        </nav>}
      </>}
    {auth.loading ? <p>Checking your session…</p> : auth.user
      ? <ReviewForm key={`${productId}:${auth.user.id}`} productId={productId} />
      : <p><Link className="text-link" to="/login">Sign in to write a review</Link></p>}
  </section>
}
