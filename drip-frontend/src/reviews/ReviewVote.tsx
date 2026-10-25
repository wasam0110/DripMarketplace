import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { Button, ErrorNotice } from '../components/ui'

export function ReviewVote({ reviewId, authorId, viewerId, helpfulCount, unhelpfulCount }: {
  reviewId: string; authorId: string; viewerId: string | null; helpfulCount: number; unhelpfulCount: number
}) {
  const lock = useRef(false)
  const [state, setState] = useState<'idle' | 'busy' | 'accepted' | 'uncertain'>('idle')
  const [error, setError] = useState<unknown>(null)
  async function vote(helpful: boolean) {
    if (lock.current || !viewerId || viewerId === authorId) return
    lock.current = true; setState('busy'); setError(null)
    try {
      const response = await request(`/reviews/${encodeURIComponent(reviewId)}/helpful`, { method: 'POST', authenticated: true, body: JSON.stringify({ helpful }) })
      if (response !== undefined) throw new Error('Unconfirmed vote response')
      setState('accepted')
    } catch (failure) {
      if (!(failure instanceof ApiError) || failure.status === 0 || failure.status >= 500) {
        setState('uncertain'); setError(new Error('Your vote could not be confirmed. It has not been retried. Do not submit another vote until its outcome is confirmed.'))
      } else { lock.current = false; setState('idle'); setError(failure) }
    }
  }
  return <div className="review-vote">
    {Number.isSafeInteger(helpfulCount) && helpfulCount >= 0 && Number.isSafeInteger(unhelpfulCount) && unhelpfulCount >= 0 &&
      <p className="muted">{helpfulCount} helpful · {unhelpfulCount} not helpful (when loaded)</p>}
    {!viewerId ? <p><Link to="/login">Sign in to vote on reviews</Link></p>
      : viewerId === authorId ? <p className="muted">You cannot vote on your own review.</p>
        : <><p>Was this review helpful? Only your first vote counts; it cannot be changed here.</p>
          <div className="option-row"><Button className="button-secondary" disabled={state !== 'idle'} onClick={() => void vote(true)}>Helpful</Button>
            <Button className="button-secondary" disabled={state !== 'idle'} onClick={() => void vote(false)}>Not helpful</Button></div></>}
    {state === 'busy' && <p role="status">Sending vote…</p>}
    {state === 'accepted' && <p role="status">Vote request accepted. If you voted earlier, your original vote was kept. Counts update when reviews are loaded again.</p>}
    {Boolean(error) && <ErrorNotice error={error} />}
  </div>
}
