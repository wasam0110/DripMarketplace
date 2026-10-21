import type { Cart } from '../api/types'

export interface CheckoutQuote extends Cart {
  currency: 'PKR'
  discount_amount: string
  quote_token: string
  quote_expires_at: string
  payment_methods: { method: string; available: boolean; unavailable_reason: string | null }[]
}

export interface CouponPreview {
  code: string
  discount_amount: string
  new_subtotal: string
}

/** Decimal strings stay exact while combining server-calculated preview amounts. */
export function paisa(value: string): bigint {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) throw new Error('Unexpected amount in the checkout preview.')
  const [whole, fraction = ''] = value.split('.')
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
}

export function previewTotal(quote: CheckoutQuote, coupon: CouponPreview | null): string {
  if (!coupon) return quote.total
  const subtotal = paisa(quote.subtotal)
  const discount = paisa(coupon.discount_amount)
  const discounted = paisa(coupon.new_subtotal)
  if (discount > subtotal || discounted + discount !== subtotal) throw new Error('The coupon preview does not match this bag. Refresh and try again.')
  const total = discounted + paisa(quote.shipping_fee)
  return `${total / 100n}.${(total % 100n).toString().padStart(2, '0')}`
}

export function validateQuote(quote: CheckoutQuote): CheckoutQuote {
  if (!quote.quote_token || !Number.isFinite(Date.parse(quote.quote_expires_at))) {
    throw new Error('The server did not provide a signed checkout quote. Refresh after the backend is updated.')
  }
  if (quote.currency !== 'PKR' || !Array.isArray(quote.items) || !quote.items.length || !Array.isArray(quote.payment_methods)) {
    throw new Error('The server returned an incomplete checkout preview.')
  }
  if (paisa(quote.subtotal) + paisa(quote.shipping_fee) - paisa(quote.discount_amount) !== paisa(quote.total)) {
    throw new Error('The checkout preview totals do not match. Please refresh.')
  }
  if (quote.items.some((item) => !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > item.available_stock)) {
    throw new Error('Stock has changed. Review your bag before continuing.')
  }
  return quote
}
