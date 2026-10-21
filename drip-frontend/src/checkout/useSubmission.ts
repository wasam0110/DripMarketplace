import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { checkoutRequest, rejectedBeforeCreation, rememberKey, savedKey, storageKey, type OrderPayload, type OrderResult } from './submission'

export function useSubmission(owner: string, onSuccess: () => void, onRejected: () => void) {
  const [initial] = useState(() => {
    try { return { key: savedKey(owner), error: null } }
    catch { return { key: null, error: new Error('Tab storage is unavailable or the saved key is invalid. Resolve this before placing an order.') } }
  })
  const key = useRef(initial.key)
  const payload = useRef<OrderPayload | null>(null)
  const lock = useRef(false)
  const alive = useRef(true)
  const [blocked, setBlocked] = useState(Boolean(initial.key || initial.error))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(initial.error)
  const [result, setResult] = useState<OrderResult | null>(null)
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])

  async function run(recovery: boolean) {
    if (lock.current || !key.current || (!recovery && !payload.current)) return
    lock.current = true; setBusy(true); setError(null); setBlocked(true)
    try {
      const order = await checkoutRequest(owner, recovery ? key.current : payload.current!)
      if (!alive.current) return
      setResult(order)
      // Recovery after reload has no item snapshot; do not erase a possibly changed guest bag.
      if (payload.current) onSuccess()
    } catch (reason) {
      if (!alive.current) return
      if (recovery && reason instanceof ApiError && reason.status === 404 && !payload.current) {
        // Reuse this key even after a not-found result: a delayed original request may still arrive.
        setBlocked(false); onRejected()
        setError(new Error('No committed order was found. Review your details again; the same checkout key will be reused.'))
      } else if (!recovery && rejectedBeforeCreation(reason)) {
        payload.current = null; setBlocked(false); onRejected(); setError(reason)
      } else setError(reason)
    } finally {
      lock.current = false
      if (alive.current) setBusy(false)
    }
  }
  function submit(body: Omit<OrderPayload, 'checkout_key'>) {
    if (lock.current || blocked || result) return
    try {
      const nextKey = key.current ?? crypto.randomUUID()
      rememberKey(owner, nextKey) // Fail closed before the network write.
      key.current = nextKey
      payload.current = { ...body, checkout_key: nextKey } as OrderPayload
      void run(false)
    } catch (reason) { setError(reason); setBlocked(true) }
  }
  function startAnother() {
    if (!result || busy) return
    try {
      sessionStorage.removeItem(storageKey(owner))
      window.location.assign('/bag')
    } catch (reason) { setError(reason) }
  }
  return { result, busy, blocked, error, submit, recover: () => void run(true),
    retry: () => void run(false), canRecover: Boolean(key.current), canRetry: Boolean(payload.current), startAnother }
}
