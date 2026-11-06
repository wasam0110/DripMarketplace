import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { moderationImage } from './products'
import { confirmReview, reviewMarker, reviewPayload, reviewQuery, reviewStatuses, sameReview, validateAdminReview, validateAdminReviews, type AdminReview, type AdminReviews } from './reviews'
import './products.css'

export function AdminReviewsPage({ detail = false }: { detail?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Review moderation</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to moderate reviews</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Customer feedback</p><h1>{detail ? 'Inspect customer review' : 'Review moderation'}</h1>
    {detail ? isOrderId(id) ? <ReviewDetail key={`${user.id}:${id}`} owner={user.id} id={id} /> : <p role="alert">This review reference is invalid.</p> : <ReviewList key={user.id} />}
  </section>
}
function ReviewList() {
  const [params, setParams] = useSearchParams(), status = params.get('status') ?? 'pending', page = params.get('page') ?? '1'
  let query = '', error: unknown = null
  try { query = reviewQuery(status, page) } catch (reason) { error = reason }
  return <><div className="account-card"><div className="field"><label htmlFor="admin-review-filter">Review status</label><select id="admin-review-filter" value={status} onChange={(event) => setParams({ status: event.target.value, page: '1' })}><option value="all">All statuses</option>{reviewStatuses.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></div></div>
    {error ? <ErrorNotice error={error} /> : <ReviewResults query={query} status={status} page={Number(page)} navigate={(next) => setParams({ status, page: String(next) })} />}</>
}
const label = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
function ReviewResults({ query, status, page, navigate }: { query: string; status: string; page: number; navigate: (page: number) => void }) {
  const validate = useCallback((value: AdminReviews) => validateAdminReviews(value, page, status), [page, status])
  const resource = useOrderRead(`/admin/reviews?${query}`, true, validate), data = resource.data
  const pages = data ? Math.max(1, Math.ceil(data.total / 25)) : 1
  return <>{resource.loading && <p role="status">Loading reviews...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{data && <>
    <p role="status">Page {page} of {pages} · {data.total} reviews</p>{!data.data.length && <EmptyState title="No reviews on this page"><p>Choose another status or try a previous page.</p></EmptyState>}
    {data.data.map((row) => <article className="account-card" key={row.id}><h2>{row.title || 'Untitled review'}</h2><p>{row.rating} / 5 · {label(row.status)} · {row.is_verified_purchase ? 'Verified purchase' : 'Purchase not verified'}</p><p>Submitted {orderDate(row.created_at)}</p><Link className="text-link" to={`/admin/reviews/${row.id}`}>Inspect review {row.id}</Link></article>)}
  </>}<div className="option-row"><Button className="button-secondary" disabled={resource.loading || page <= 1} onClick={() => navigate(page - 1)}>Previous review page</Button><Button className="button-secondary" disabled={resource.loading || !data || page >= pages} onClick={() => navigate(page + 1)}>Next review page</Button><Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh review list</Button></div></>
}
function ReviewDetail({ owner, id }: { owner: string; id: string }) {
  const path = `/admin/reviews/${id}`, validate = useCallback((value: AdminReview) => validateAdminReview(value, id), [id])
  const resource = useOrderRead(path, true, validate), write = useAccountWrite()
  const active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(reviewMarker(owner, id)) !== null } catch { return true } })
  const disabled = resource.loading || write.busy || write.blocked || pending
  function refresh() { resource.retry() }
  function save(before: AdminReview, payload: ReturnType<typeof reviewPayload>) {
    if (disabled) return
    void write.run(async () => {
      let sent = false
      try {
        const latest = validate(await request<AdminReview>(path, { authenticated: true, cache: 'no-store' }))
        if (!active.current) throw new Error('This review session is no longer active. No change was sent.')
        if (!sameReview(before, latest)) { refresh(); throw new Error('The review changed. Inspect the refreshed content before deciding.') }
        sessionStorage.setItem(reviewMarker(owner, id), 'pending'); setPending(true); sent = true
        confirmReview(await request<AdminReview>(path, { authenticated: true, method: 'PATCH', body: JSON.stringify(payload) }), before, payload)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The review could not be rechecked. No change was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(reviewMarker(owner, id)); setPending(false) }
        throw reason
      }
      try { confirmReview(await request<AdminReview>(path, { authenticated: true, cache: 'no-store' }), before, payload) }
      catch { throw new Error('The moderation decision could not be confirmed. Inspect the saved review before repeating it.') }
      sessionStorage.removeItem(reviewMarker(owner, id)); setPending(false)
    }, refresh, 'Review moderation saved and confirmed.')
  }
  const row = resource.data
  return <><p><Link className="text-link" to="/admin/reviews">Back to review moderation</Link></p>{resource.loading && <p role="status">Loading review detail...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={write} />
    {pending && !write.busy && <p role="alert">A review decision is awaiting confirmation. Inspect the saved review or contact support before another change.</p>}
    {row && <>
      <section className="account-card"><h2>{row.title || 'Untitled review'}</h2><p className="admin-product-copy">{row.body || 'No review text supplied.'}</p><dl><dt>Rating</dt><dd>{row.rating} / 5</dd><dt>Status</dt><dd>{label(row.status)}</dd><dt>Author</dt><dd>{[row.user.first_name, row.user.last_name].filter(Boolean).join(' ') || 'Name unavailable'}</dd><dt>Author reference</dt><dd>{row.user.id}</dd><dt>Purchase</dt><dd>{row.is_verified_purchase ? 'Verified purchase' : 'Purchase not verified'}</dd><dt>Submitted</dt><dd>{orderDate(row.created_at)}</dd><dt>Last updated</dt><dd>{orderDate(row.updated_at)}</dd><dt>Last moderated</dt><dd>{row.moderated_at ? orderDate(row.moderated_at) : 'Not recorded'}</dd><dt>Helpful / unhelpful votes</dt><dd>{row.helpful_count} / {row.unhelpful_count}</dd><dt>Private moderation note</dt><dd className="admin-product-copy">{row.admin_note || 'Not supplied'}</dd></dl><p><Link className="text-link" to={`/admin/products/${row.product_id}`}>Inspect reviewed product</Link></p></section>
      <section className="account-card"><h2>Review photos</h2>{!row.images.length && <p>No review photos supplied.</p>}<div className="admin-product-images">{[...row.images].sort((a, b) => a.sort_order - b.sort_order || a.id.localeCompare(b.id)).map((image, index) => <figure key={image.id}>{moderationImage(image.url) ? <img src={moderationImage(image.url)!} alt={`Customer review photo ${index + 1}`} loading="lazy" referrerPolicy="no-referrer" /> : <p>Image URL unavailable.</p>}<figcaption>Photo {index + 1}</figcaption></figure>)}</div></section>
      <ReviewForm key={row.updated_at} row={row} disabled={disabled} save={save} />
    </>}<Button className="button-secondary" disabled={resource.loading || write.busy} onClick={refresh}>Refresh review and discard decision</Button></>
}
function ReviewForm({ row, disabled, save }: { row: AdminReview; disabled: boolean; save: (row: AdminReview, payload: ReturnType<typeof reviewPayload>) => void }) {
  const [status, setStatus] = useState(row.status === 'pending' ? 'approved' : row.status), [note, setNote] = useState(row.admin_note ?? '')
  const [review, setReview] = useState<ReturnType<typeof reviewPayload> | null>(null), [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled || review) return; try { setReview(reviewPayload(status, note, row)); setError(null) } catch (reason) { setError(reason) } }}>
    <h2>Moderation decision</h2><p>Only approved reviews appear publicly and contribute to product ratings. This does not edit customer content, remove photos or delete the review. Notes are private to administrators.</p>
    <div className="field"><label htmlFor="admin-review-decision">Decision</label><select id="admin-review-decision" value={status} disabled={disabled || !!review} onChange={(event) => setStatus(event.target.value as typeof status)}>{['approved', 'rejected', 'hidden'].map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></div>
    <div className="field"><label htmlFor="admin-review-note">Private admin note (optional)</label><textarea id="admin-review-note" rows={4} maxLength={1000} value={note} disabled={disabled || !!review} onChange={(event) => setNote(event.target.value)} /><small>Up to 1,000 characters. Clearing this field removes the previous note.</small></div>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review moderation decision</Button>
    {review && <div className="admin-product-confirm"><h3>Confirm {review.status} decision</h3><p>Review reference: {row.id}</p><p className="admin-product-copy">Private note: {review.admin_note || 'Clear / no note'}</p><div className="option-row"><Button disabled={disabled} onClick={() => save(row, review)}>Confirm review moderation</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to decision</Button></div></div>}
  </form>
}
