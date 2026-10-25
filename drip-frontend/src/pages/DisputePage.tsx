import { useCallback, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { AccountGate, useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, ErrorNotice } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { validateReturnDetail, type ReturnDetail } from '../orders/returnHistory'
import { canMessage, disputeStatus, disputeText, missingDispute, validateDispute, validateMessage, type DisputeDetail, type DisputeMessage } from '../orders/disputes'

export function DisputePage() {
  const { id = '' } = useParams()
  if (!isOrderId(id)) return <section className="container page"><h1>Dispute unavailable</h1><Link to="/returns">Your returns</Link></section>
  return <AccountGate title="Return dispute">{(owner) => <DisputeManager key={`${owner}:${id}`} id={id} owner={owner} />}</AccountGate>
}
function DisputeManager({ id, owner }: { id: string; owner: string }) {
  const validateReturn = useCallback((value: ReturnDetail) => validateReturnDetail(value, id), [id])
  const validate = useCallback((value: DisputeDetail) => validateDispute(value, id), [id])
  const returned = useOrderRead(`/returns/${id}`, true, validateReturn)
  const dispute = useOrderRead(`/returns/${id}/dispute`, true, validate)
  // Both read refreshes preserve this guard and the last confirmed write reference.
  const write = useAccountWrite()
  const [opened, setOpened] = useState(false)
  const [confirmedMessage, setConfirmedMessage] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [review, setReview] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const absent = missingDispute(dispute.error)
  const opening = Boolean(returned.data?.status === 'rejected' && absent && !opened)
  const awaitingMessage = Boolean(confirmedMessage && !dispute.data?.messages.some((message) => message.id === confirmedMessage))
  const mayReply = Boolean(dispute.data && canMessage(dispute.data.status) && !awaitingMessage)
  const disabled = !returned.data || returned.loading || dispute.loading || write.busy || write.blocked || (!opening && !mayReply)
  function refresh() { setReview(false); returned.retry(); dispute.retry() }
  function prepare(event: FormEvent) {
    event.preventDefault(); if (disabled) return
    try { setDraft(disputeText(draft, opening)); setError(null); setReview(true) } catch (reason) { setError(reason) }
  }
  function submit() {
    if (disabled || !review) return
    const text = disputeText(draft, opening)
    if (opening) {
      void write.run(async () => {
        const result = validate(await request<DisputeDetail>(`/returns/${id}/dispute`, { authenticated: true, method: 'POST', body: JSON.stringify({ message: text }) }))
        if (result.status !== 'open' || !result.messages.some((message) => message.sender_id === owner && message.body === text)) throw new Error('The opened dispute could not be confirmed. Do not repeat it until you check its status.')
        return result
      }, () => { setOpened(true); setDraft(''); refresh() }, 'Dispute opened. This does not approve a return or confirm a refund.')
    } else {
      void write.run(async () => {
        const result = validateMessage(await request<DisputeMessage>(`/returns/${id}/dispute/messages`, { authenticated: true, method: 'POST', body: JSON.stringify({ body: text }) }))
        if (result.sender_id !== owner || result.body !== text || dispute.data?.messages.some((message) => message.id === result.id)) throw new Error('The message could not be confirmed. Check the conversation before sending it again.')
        return result
      }, (message) => { setConfirmedMessage(message.id); setDraft(''); refresh() }, 'Message sent.')
    }
  }
  return <>
    <p><Link to={`/returns/${id}`}>Back to return details</Link></p>
    <p>Only rejected account returns can open a dispute. Decisions and messages come from the backend; no refund is promised here.</p>
    {(returned.loading || dispute.loading) && <p role="status">Loading dispute information…</p>}
    {Boolean(returned.error) && <ErrorNotice error={new Error('Return access could not be verified. Refresh or sign in to its owning account.')} />}
    <WriteFeedback state={write} />
    {returned.data && !returned.loading && <>
      {Boolean(dispute.error) && !absent && <ErrorNotice error={dispute.error instanceof ApiError && [401, 403, 404].includes(dispute.error.status) ? new Error('Dispute access could not be verified. No changes can be made.') : dispute.error} />}
      {absent && <p>{opened ? 'The dispute was created, but its latest details are unavailable. Refresh or contact support; do not open it again.' : 'No dispute exists for this return.'}</p>}
      {absent && returned.data.status !== 'rejected' && <p>A new dispute is available only after a return is rejected.</p>}
      {dispute.data && <article className="account-card" aria-label="Dispute conversation">
        <h2>{disputeStatus(dispute.data.status)}</h2><p>Dispute reference: {dispute.data.id}</p>
        <p>Opened: {orderDate(dispute.data.created_at)}</p>
        {dispute.data.resolved_at && <p>Resolved: {orderDate(dispute.data.resolved_at)}</p>}
        {dispute.data.resolution_note && <><h3>Resolution note</h3><p className="request-reason">{dispute.data.resolution_note}</p></>}
        <h3>Messages</h3>{!dispute.data.messages.length && <p>No messages available.</p>}
        <ol className="order-items">{dispute.data.messages.map((message) => <li key={message.id}><strong>{message.sender_id === owner ? 'You' : 'Other participant'}</strong><p>{orderDate(message.created_at)}</p><p className="request-reason">{message.body}</p></li>)}</ol>
        {!canMessage(dispute.data.status) && <p>This dispute is closed, resolved or has an unsupported status. New messages are disabled.</p>}
      </article>}
      {awaitingMessage && <p className="notice">Your message was confirmed, but is not in the latest conversation yet. Refresh before sending another.</p>}
      {(opening || mayReply) && <form className="checkout-form" onSubmit={prepare}>
        <h2>{opening ? 'Open a dispute' : 'Add a message'}</h2>
        <p id="dispute-privacy">Do not include passwords, bank details or private access codes. Unsaved text stays in this page; confirmed messages are sent to the server.</p>
        {!review ? <><label className="field" htmlFor="dispute-message">{opening ? 'Explain your dispute' : 'Your message'}</label>
          <textarea id="dispute-message" rows={5} maxLength={2000} required value={draft} disabled={disabled} aria-describedby="dispute-privacy" onChange={(event) => setDraft(event.target.value)} />
          {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled}>Review message</Button>
        </> : <><h3>Review before sending</h3><p className="request-reason">{draft}</p>
          <Button disabled={disabled} onClick={submit}>{opening ? 'Confirm opening dispute' : 'Confirm send message'}</Button>
          <Button className="button-secondary" disabled={write.busy} onClick={() => setReview(false)}>Edit message</Button></>}
      </form>}
    </>}
    <Button className="button-secondary" disabled={write.busy || returned.loading || dispute.loading} onClick={refresh}>Refresh dispute</Button>
  </>
}
