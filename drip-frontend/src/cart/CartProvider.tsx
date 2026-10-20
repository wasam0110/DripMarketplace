import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { refreshSession, request } from '../api/client'
import type { Cart, ProductDetail, ProductVariant } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { changeGuestQuantity, GUEST_CART_KEY, readGuestBag, remainingAfterMerge, writeGuestBag, type GuestSelection } from './guestStorage'

const emptyCart = (): Cart => ({ items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' })
const selectionPayload = (items: GuestSelection[]) => items.map(({ variant_id, quantity }) => ({ variant_id, quantity }))

interface BagContext {
  cart: Cart | null
  guest: GuestSelection[]
  loading: boolean
  busy: boolean
  error: unknown
  storageError: unknown
  needsReview: boolean
  notice: string
  count: number
  reload: () => void
  add: (product: ProductDetail, variant: ProductVariant, quantity: number) => Promise<void>
  update: (variantId: string, quantity: number) => Promise<void>
  clear: () => Promise<void>
  merge: () => Promise<void>
}

const CartContext = createContext<BagContext | null>(null)

export function CartProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading, error: authError } = useAuth()
  const owner = user ? user.id : 'guest'
  const ownerRef = useRef(owner)
  ownerRef.current = owner
  const [guest, setGuest] = useState<GuestSelection[]>([])
  const [storageError, setStorageError] = useState<unknown>(null)
  const [storageReady, setStorageReady] = useState(false)
  const [snapshot, setSnapshot] = useState<{ owner: string; cart: Cart } | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [needsReview, setNeedsReview] = useState(false)
  const [notice, setNotice] = useState('')
  const [attempt, setAttempt] = useState(0)
  const generation = useRef(0)
  const mutation = useRef<symbol | null>(null)
  const cart = snapshot?.owner === owner ? snapshot.cart : null

  useEffect(() => { setNotice(''); setNeedsReview(false) }, [owner])

  useEffect(() => {
    function loadStorage() {
      try { setGuest(readGuestBag()); setStorageError(null) }
      catch (reason) { setGuest([]); setStorageError(reason) }
      setStorageReady(true)
    }
    loadStorage()
    function storageChanged(event: StorageEvent) {
      if (event.key === GUEST_CART_KEY || event.key === null) loadStorage()
    }
    window.addEventListener('storage', storageChanged)
    return () => window.removeEventListener('storage', storageChanged)
  }, [])

  useEffect(() => {
    const current = ++generation.current
    const controller = new AbortController()
    setSnapshot(null); setError(null)
    if (authLoading || !storageReady) { setLoading(true); return }
    // A failed auth restoration is not proof that the visitor is a guest.
    if (authError && !user) { setError(new Error(authError)); setLoading(false); return }
    setLoading(true)
    const pending = user
      ? request<Cart>('/cart', { authenticated: true, signal: controller.signal })
      : guest.length
        ? request<Cart>('/orders/guest/quote', {
          method: 'POST', body: JSON.stringify({ items: selectionPayload(guest) }), signal: controller.signal,
        })
        : Promise.resolve(emptyCart())
    pending.then((result) => {
      if (current === generation.current && ownerRef.current === owner && !controller.signal.aborted) {
        if (!Array.isArray(result.items)) throw new Error('The server returned an unexpected bag response.')
        setSnapshot({ owner, cart: result }); setNeedsReview(false)
      }
    }).catch((reason: unknown) => {
      if (current === generation.current && !controller.signal.aborted) setError(reason)
    }).finally(() => {
      if (current === generation.current) setLoading(false)
    })
    return () => controller.abort()
  }, [owner, authLoading, authError, storageReady, guest, attempt, user])

  function save(items: GuestSelection[]) {
    writeGuestBag(items)
    setGuest(items)
    setStorageError(null)
  }

  async function perform(operation: (isGuest: boolean, assertOwner: () => void) => Promise<void>) {
    if (authLoading || !storageReady || (!user && authError)) throw new Error('Your session is not ready. Please sign in or reload before changing your bag.')
    if (mutation.current) throw new Error('Please wait for the current bag update.')
    if (needsReview) throw new Error('Refresh your bag and review its quantities before trying another change.')
    const ticket = Symbol()
    mutation.current = ticket
    const capturedOwner = owner
    const assertOwner = () => {
      if (ownerRef.current !== capturedOwner) throw new Error('Your account changed. Please review the current bag.')
    }
    setBusy(true); setError(null); setNotice('')
    // Invalidate an older bag read so it cannot overwrite the mutation result.
    generation.current += 1
    try {
      if (user) { await refreshSession(); assertOwner() }
      await operation(!user, assertOwner)
    } catch (reason) {
      if (ownerRef.current === capturedOwner) {
        setError(reason)
        if (user) setNeedsReview(true)
      }
      throw reason
    } finally {
      if (mutation.current === ticket) { mutation.current = null; setBusy(false); setLoading(false) }
    }
  }

  async function add(product: ProductDetail, variant: ProductVariant, quantity: number) {
    if (!variant.is_active || !Number.isInteger(quantity) || quantity < 1 || quantity > Math.min(variant.available_stock, 100)) {
      throw new Error('Choose an available size and quantity.')
    }
    await perform(async (isGuest, assertOwner) => {
      if (isGuest) {
        const current = readGuestBag()
        const total = (current.find((item) => item.variant_id === variant.id)?.quantity ?? 0) + quantity
        if (total > Math.min(variant.available_stock, 100)) throw new Error('Your bag would exceed the available stock for this variant.')
        save(changeGuestQuantity(current, { product_id: product.id, variant_id: variant.id, quantity }, total))
      } else {
        const result = await request<Cart>('/cart', {
          method: 'POST', authenticated: true, body: JSON.stringify({ variant_id: variant.id, quantity }),
        })
        assertOwner(); setSnapshot({ owner, cart: result })
      }
    })
  }

  async function update(variantId: string, quantity: number) {
    if (!Number.isInteger(quantity) || quantity < 0 || quantity > 100) throw new Error('Choose a valid quantity.')
    await perform(async (isGuest, assertOwner) => {
      if (isGuest) {
        const current = readGuestBag()
        const selected = current.find((item) => item.variant_id === variantId)
        if (!selected) return
        const live = cart?.items.find((item) => item.variant_id === variantId)
        if (quantity > selected.quantity && (!live || quantity > live.available_stock)) {
          throw new Error('Refresh your bag or choose a quantity within the available stock.')
        }
        save(changeGuestQuantity(current, selected, quantity))
      } else {
        const result = await request<Cart>(`/cart/${encodeURIComponent(variantId)}`, {
          method: 'PATCH', authenticated: true, body: JSON.stringify({ quantity }),
        })
        assertOwner(); setSnapshot({ owner, cart: result })
      }
    })
  }

  async function clear() {
    await perform(async (isGuest, assertOwner) => {
      if (isGuest) save([])
      else {
        await request('/cart/clear', { method: 'POST', authenticated: true })
        assertOwner(); setSnapshot({ owner, cart: emptyCart() })
      }
    })
  }

  async function merge() {
    if (!user) return
    await perform(async (_isGuest, assertOwner) => {
      const sent = readGuestBag()
      if (!sent.length) return
      const result = await request<Cart>('/cart/sync', {
        method: 'POST', authenticated: true, body: JSON.stringify({ items: selectionPayload(sent) }),
      })
      assertOwner()
      const remaining = remainingAfterMerge(readGuestBag(), sent, new Set(result.items.map((item) => item.variant_id)))
      save(remaining)
      setSnapshot({ owner, cart: result })
      setNotice(remaining.length ? 'Some guest selections could not be merged. They are still saved on this device.' : 'Your guest pieces are now in this account’s bag.')
    })
  }

  return <CartContext.Provider value={{
    cart, guest, loading, busy, error, storageError, needsReview, notice,
    count: user ? (cart?.item_count ?? 0) : guest.reduce((sum, item) => sum + item.quantity, 0),
    reload: () => setAttempt((value) => value + 1), add, update, clear, merge,
  }}>{children}</CartContext.Provider>
}

export function useCart() {
  const value = useContext(CartContext)
  if (!value) throw new Error('useCart must be used inside CartProvider')
  return value
}
