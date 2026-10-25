import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Button } from '../components/ui'
import type { OrderDetail } from './api'
import { returnPayload, type ReturnPayload } from './returns'

/** Keeps drafts local; the parent owns cancellation authorization and write state. */
export function RequestPreview({ order, cancellation, returns }: { order: OrderDetail; cancellation?: { disabled: boolean; busy?: boolean; submit: (reason: string) => void }; returns?: { disabled: boolean; submit: (payload: ReturnPayload) => void } }) {
  const [mode, setMode] = useState<'cancel' | 'return' | null>(null)
  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [reason, setReason] = useState('')
  const [review, setReview] = useState(false)
  const [error, setError] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)
  const selected = order.items.filter((item) => item.id in quantities)
  useEffect(() => {
    if (mode) { wasOpen.current = true; heading.current?.focus() }
    else if (wasOpen.current) { wasOpen.current = false; launcher.current?.focus() }
  }, [mode, review])

  function open(next: 'cancel' | 'return') {
    setMode(next); setQuantities({}); setReason(''); setError(''); setReview(false)
  }
  function close() {
    setMode(null); setQuantities({}); setReason(''); setError(''); setReview(false)
  }
  function prepare(event: FormEvent) {
    event.preventDefault()
    if (mode === 'return' && !selected.length) { setError('Select at least one piece to preview a return.'); return }
    if (!reason.trim()) { setError('Describe the reason before reviewing your draft.'); return }
    if (selected.some((item) => !Number.isInteger(quantities[item.id]) || quantities[item.id] < 1 || quantities[item.id] > item.quantity)) {
      setError('Choose a quantity between one and the purchased quantity.'); return
    }
    if (mode === 'return' && returns) {
      try { returnPayload(order, quantities, reason) } catch (error) { setError((error as Error).message); return }
    }
    setReason(reason.trim()); setError(''); setReview(true)
  }

  return <section className="order-request" aria-label="Cancellation and returns">
    {!mode ? <>
      <h2>Need to change something?</h2>
      <p>{returns ? 'Review a cancellation or a return for one brand before confirming.' : cancellation ? 'Review a whole-order cancellation before confirming. Returns are preview-only.' : 'Preview a cancellation or return request. Submission is not enabled yet.'}</p>
      <div className="option-row"><button ref={launcher} className="button button-secondary" type="button" onClick={() => open('cancel')}>Preview cancellation</button>
        <Button className="button-secondary" onClick={() => open('return')}>Preview a return</Button></div>
    </> : <>
      <p className="eyebrow">{order.order_number} · Unsaved draft</p>
      <h2 ref={heading} tabIndex={-1}>{review ? 'Review your draft' : mode === 'cancel' ? 'Cancellation preview' : 'Return preview'}</h2>
      <p className="notice" id="request-preview-limit">{mode === 'return' && returns ? 'Select pieces from one brand only. Returns require a delivered or completed order. The server checks eligibility and previously claimed quantities. Submission is not approval or a refund; wait for return instructions.' : mode === 'cancel' && cancellation ? 'Confirmation requests cancellation of every item in this order. The server checks current eligibility. Paid orders require support; this action does not issue a refund.' : 'Frontend preview only. Nothing has been submitted. Eligibility, time limits, returnable quantities and refund amounts have not been checked.'}</p>
      {!review ? <form className="checkout-form" onSubmit={prepare}>
        {mode === 'cancel' ? <p>This draft concerns the whole order. It does not cancel any items or stop a shipment.</p> : <fieldset className="request-pieces"><legend>Choose pieces to include</legend>
          {!order.items.length && <p>No order items are available to select.</p>}
          {order.items.map((item) => <div className="request-piece" key={item.id}>
            {returns && <p className="muted">{order.seller_orders.find((shipment) => shipment.seller_id === item.seller_id)?.brand_name ?? 'Brand shipment unavailable'}</p>}
            <label><input type="checkbox" checked={item.id in quantities} onChange={(event) => {
              const checked = event.target.checked
              setQuantities((current) => { const next = { ...current }; if (checked) next[item.id] = 1; else delete next[item.id]; return next }); setError('')
            }} /> <span>{item.product_name}<small>{item.variant_label} · Purchased: {item.quantity}</small></span></label>
            {item.id in quantities && <label className="field">Quantity for {item.product_name}
              <input type="number" inputMode="numeric" min={1} max={item.quantity} required value={quantities[item.id]} onChange={(event) => {
                setQuantities((current) => ({ ...current, [item.id]: Number(event.target.value) || 0 }))
              }} /></label>}
          </div>)}
          <p className="muted">Purchased quantities are shown for drafting only. Previous returns and brand-specific eligibility still need verification.</p>
        </fieldset>}
        <div className="field"><label htmlFor="request-reason">Reason for your {mode === 'cancel' ? 'cancellation' : 'return'} draft</label>
          <textarea id="request-reason" rows={4} required maxLength={mode === 'return' && returns ? 1000 : 500} value={reason} onChange={(event) => setReason(event.target.value)} aria-describedby="request-privacy" /></div>
        <p className="muted" id="request-privacy">Keep bank details and other sensitive information out of this draft. Unsaved text stays in page memory and disappears when you leave or refresh. Confirming a request sends its reason and selection to the server.</p>
        {error && <p className="field-error" role="alert">{error}</p>}
        <Button type="submit">Review draft</Button>
      </form> : <div className="checkout-form">
        <h3>{mode === 'cancel' ? 'Whole-order cancellation draft' : 'Selected return pieces'}</h3>
        {mode === 'return' && <ul className="order-items">{selected.map((item) => <li key={item.id}><strong>{item.product_name}</strong><p>{item.variant_label} · Quantity: {quantities[item.id]}</p></li>)}</ul>}
        <h3>Your reason</h3><p className="request-reason">{reason}</p>
        <p>No refund estimate or approval is available. Do not send any items back based on this preview.</p>
        {mode === 'return' && returns ? <Button disabled={returns.disabled} aria-describedby="request-preview-limit" onClick={() => {
          try { returns.submit(returnPayload(order, quantities, reason)) } catch (error) { setError((error as Error).message); setReview(false) }
        }}>Confirm return request</Button> : mode === 'cancel' && cancellation ? <Button disabled={cancellation.disabled} aria-describedby="request-preview-limit" onClick={() => cancellation.submit(reason)}>Yes, cancel the whole order</Button> : <Button disabled aria-describedby="request-preview-limit">{mode === 'cancel' ? 'Submit cancellation — unavailable' : 'Submit return — unavailable'}</Button>}
        <Button className="button-secondary" disabled={cancellation?.busy} onClick={() => setReview(false)}>Edit draft</Button>
      </div>}
      <Button className="button-secondary" disabled={cancellation?.busy} onClick={close}>Discard draft</Button>
    </>}
  </section>
}
