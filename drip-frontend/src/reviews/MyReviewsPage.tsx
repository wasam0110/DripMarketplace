import { useCallback, useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { isOrderId, useOrderRead } from '../orders/api'

interface OwnReview {
  id: string; product_id: string; user: { id: string }; rating: number
  title: string | null; body: string | null; status: string
}
function validateReview(row: OwnReview, owner: string) {
  if (!row || !isOrderId(row.id) || !isOrderId(row.product_id) || row.user?.id !== owner ||
    !Number.isInteger(row.rating) || row.rating < 1 || row.rating > 5 ||
    !['pending', 'approved', 'rejected'].includes(row.status) ||
    (row.title !== null && typeof row.title !== 'string') || (row.body !== null && typeof row.body !== 'string')) {
    throw new Error('Review information could not be verified. Refresh your reviews.')
  }
  return row
}

export function MyReviewsPage() {
  const auth = useAuth()
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  if (!auth.user || auth.error) return <section className="container page"><h1>Your reviews</h1><p>Sign in to manage your reviews.</p><Link className="button" to="/login">Sign in</Link></section>
  return <ReviewManager key={auth.user.id} owner={auth.user.id} />
}

function ReviewManager({ owner }: { owner: string }) {
  const [page, setPage] = useState(1)
  const [blocked, setBlocked] = useState(false)
  const [writing, setWriting] = useState(false)
  const validate = useCallback((rows: OwnReview[]) => {
    if (!Array.isArray(rows)) throw new Error('The server returned unexpected review information.')
    return rows.map((row) => validateReview(row, owner))
  }, [owner])
  const resource = useOrderRead(`/me/reviews?page=${page}&per_page=20`, true, validate)
  return <section className="container page">
    <Link className="text-link" to="/account">Back to account</Link><p className="eyebrow">Your perspective</p><h1>Your reviews</h1>
    <p>Manage reviews you have written. Changes return a review to moderation before it appears publicly again.</p>
    {blocked && <p className="notice" role="alert">A change could not be confirmed. Further changes are blocked in this session. Refresh to inspect the current server state, but do not repeat the change until its outcome is confirmed with support.</p>}
    {resource.loading && <p role="status">Loading your reviews…</p>}
    {Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>
      {!resource.data.length && <p>{page === 1 ? 'You have not written any reviews yet.' : 'No reviews on this page. Return to the previous page.'}</p>}
      <div>{resource.data.map((review) => <ManagedReview key={review.id} initial={review} owner={owner} blocked={blocked || writing} onBusy={setWriting} onUncertain={() => setBlocked(true)} />)}</div>
      <nav className="pagination" aria-label="Your review pages">
        <Button disabled={page === 1 || writing} onClick={() => setPage((value) => value - 1)}>Previous reviews</Button><span>Page {page}</span>
        <Button disabled={resource.data.length < 20 || writing} onClick={() => setPage((value) => value + 1)}>Next reviews</Button>
      </nav>
    </>}
    <Button className="button-secondary" disabled={resource.loading || writing} onClick={resource.retry}>Refresh your reviews</Button>
  </section>
}

function ManagedReview({ initial, owner, blocked, onBusy, onUncertain }: { initial: OwnReview; owner: string; blocked: boolean; onBusy: (busy: boolean) => void; onUncertain: () => void }) {
  const [review, setReview] = useState(initial)
  const [mode, setMode] = useState<'view' | 'edit' | 'delete'>('view')
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const [deleted, setDeleted] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState<unknown>(null)
  const fieldId = useId()
  async function mutate(method: 'PATCH' | 'DELETE', body?: { rating: number; title: string; body: string }) {
    if (lock.current || blocked) return
    lock.current = true; setBusy(true); onBusy(true); setError(null); setNotice('')
    try {
      const response = await request<OwnReview | undefined>(`/me/reviews/${review.id}`, { authenticated: true, method, ...(body ? { body: JSON.stringify(body) } : {}) })
      if (method === 'DELETE') {
        if (response !== undefined) throw new Error('Unconfirmed deletion')
        setDeleted(true)
      } else {
        const confirmed = validateReview(response!, owner)
        if (confirmed.id !== review.id || confirmed.product_id !== review.product_id || confirmed.status !== 'pending') throw new Error('Unconfirmed update')
        setReview(confirmed); setMode('view'); setNotice('Changes saved and awaiting moderation.')
      }
    } catch (failure) {
      if (!(failure instanceof ApiError) || failure.status === 0 || failure.status >= 500) onUncertain()
      else setError(failure)
    } finally { lock.current = false; setBusy(false); onBusy(false) }
  }
  if (deleted) return <p role="status" className="notice">Review deleted. This cannot be undone.</p>
  return <article className="order-card" aria-label={`Your review: ${review.title || 'Untitled review'}`}>
    <p className="eyebrow">{review.status === 'pending' ? 'Awaiting moderation' : review.status === 'approved' ? 'Published' : 'Rejected'}</p>
    <h2>{review.title || 'Untitled review'}</h2><p>{review.rating} out of 5</p>
    <p className="review-body">{review.body}</p><Link className="text-link" to={`/products/${review.product_id}`}>View product</Link>
    <p><Link to={`/account/reviews/${review.id}/photos`}>Manage review photos</Link></p>
    {notice && <p role="status">{notice}</p>}{Boolean(error) && <ErrorNotice error={error} />}
    {mode === 'view' && <div className="option-row">
      {review.status !== 'rejected' && <Button disabled={blocked || busy} onClick={() => { setMode('edit'); setError(null) }}>Edit review</Button>}
      <Button className="button-secondary" disabled={blocked || busy} onClick={() => { setMode('delete'); setError(null) }}>Delete review</Button>
    </div>}
    {review.status === 'rejected' && <p>Rejected reviews cannot be edited.</p>}
    {mode === 'edit' && <form className="review-form" onSubmit={(event) => {
      event.preventDefault()
      const fields = new FormData(event.currentTarget)
      const rating = Number(fields.get('rating')), title = String(fields.get('title') ?? '').trim(), body = String(fields.get('body') ?? '').trim()
      if (!Number.isInteger(rating) || rating < 1 || rating > 5 || title.length > 200 || body.length > 2000) { setError(new Error('Check the rating and review length.')); return }
      void mutate('PATCH', { rating, title, body })
    }}>
      <p>Saving removes an approved review from public display until it is approved again.</p>
      <fieldset className="review-fields" disabled={busy || blocked}><legend className="sr-only">Edit your review</legend>
        <div className="field"><label htmlFor={`${fieldId}-rating`}>Rating</label><select id={`${fieldId}-rating`} name="rating" defaultValue={review.rating}>{[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} out of 5</option>)}</select></div>
        <Field label="Review title" name="title" maxLength={200} defaultValue={review.title ?? ''} />
        <div className="field"><label htmlFor={`${fieldId}-body`}>Review text</label><textarea id={`${fieldId}-body`} name="body" rows={5} maxLength={2000} defaultValue={review.body ?? ''} /></div>
        <div className="option-row"><Button type="submit">{busy ? 'Saving…' : 'Save review changes'}</Button><Button className="button-secondary" onClick={() => setMode('view')}>Cancel editing</Button></div>
      </fieldset>
    </form>}
    {mode === 'delete' && <div className="notice"><p>Delete this review permanently? Its text and rating will be removed. This cannot be undone.</p>
      <div className="option-row"><Button disabled={busy || blocked} onClick={() => void mutate('DELETE')}>{busy ? 'Deleting…' : 'Yes, delete review'}</Button>
        <Button className="button-secondary" disabled={busy} onClick={() => setMode('view')}>Keep review</Button></div>
    </div>}
  </article>
}
