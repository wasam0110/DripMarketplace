export const GUEST_CART_KEY = 'wearhowz.guest-bag.v1'
export const MAX_BAG_LINES = 100

// Persist selection identifiers only; prices, stock and totals always come from the API.
export interface GuestSelection {
  product_id: string
  variant_id: string
  quantity: number
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function parseGuestBag(raw: string | null): GuestSelection[] {
  if (raw === null) return []
  const data: unknown = JSON.parse(raw)
  if (!Array.isArray(data) || data.length > MAX_BAG_LINES) throw new Error('Invalid saved bag.')
  const seen = new Set<string>()
  return data.map((entry: unknown) => {
    if (!entry || typeof entry !== 'object') throw new Error('Invalid saved item.')
    const item = entry as Record<string, unknown>
    if (typeof item.product_id !== 'string' || !uuid.test(item.product_id)
      || typeof item.variant_id !== 'string' || !uuid.test(item.variant_id)
      || typeof item.quantity !== 'number' || !Number.isInteger(item.quantity)
      || item.quantity < 1 || item.quantity > 100 || seen.has(item.variant_id)) {
      throw new Error('Invalid saved item.')
    }
    seen.add(item.variant_id)
    return { product_id: item.product_id, variant_id: item.variant_id, quantity: item.quantity }
  })
}

export function readGuestBag(): GuestSelection[] {
  try { return parseGuestBag(localStorage.getItem(GUEST_CART_KEY)) }
  catch { throw new Error('We couldn’t read the saved bag on this device. It has not been overwritten. You can clear it below to start again.') }
}

export function writeGuestBag(items: GuestSelection[]) {
  const serialized = JSON.stringify(items)
  parseGuestBag(serialized)
  try {
    if (items.length) localStorage.setItem(GUEST_CART_KEY, serialized)
    else localStorage.removeItem(GUEST_CART_KEY)
  } catch {
    throw new Error('Your browser couldn’t save this bag. Allow site storage or sign in to use a server-saved bag.')
  }
}

export function changeGuestQuantity(
  items: GuestSelection[], selection: GuestSelection, quantity: number,
): GuestSelection[] {
  if (!Number.isInteger(quantity) || quantity < 0 || quantity > 100) throw new Error('Choose a quantity from 1 to 100.')
  const next = items.filter((item) => item.variant_id !== selection.variant_id)
  if (quantity) next.push({ ...selection, quantity })
  if (next.length > MAX_BAG_LINES) throw new Error('Your bag can contain up to 100 different variants.')
  return next
}

/** Preserve selections changed in another tab while the merge request was running. */
export function remainingAfterMerge(current: GuestSelection[], sent: GuestSelection[], accepted: Set<string>) {
  return current.filter((item) => !accepted.has(item.variant_id)
    || !sent.some((old) => old.variant_id === item.variant_id && old.product_id === item.product_id && old.quantity === item.quantity))
}
