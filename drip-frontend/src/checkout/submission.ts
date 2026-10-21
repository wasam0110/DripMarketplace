import { ApiError, refreshSession, request } from '../api/client'
import { paisa } from './preview'

export interface OrderResult {
  order_id: string
  order_number: string
  status: string
  total: string
  payment_method: string
  guest_token: string | null
  whatsapp_url: string | null
}
export type OrderPayload = Record<string, unknown> & { quote_token: string; checkout_key: string }
const uuid4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
export const storageKey = (owner: string) => `wearhowz.checkout.v1:${owner}`

/** Store only the owner-scoped recovery capability; never contact data or the payload. */
export function savedKey(owner: string): string | null {
  const key = sessionStorage.getItem(storageKey(owner))
  if (key && !uuid4.test(key)) throw new Error('The saved checkout key is invalid. Contact support before placing another order.')
  return key
}
export function rememberKey(owner: string, key: string) {
  if (!uuid4.test(key)) throw new Error('A secure checkout key could not be generated.')
  sessionStorage.setItem(storageKey(owner), key)
  if (savedKey(owner) !== key) throw new Error('Allow tab storage before placing an order, so it can be recovered safely.')
}
export function validateOrder(result: OrderResult): OrderResult {
  if (!result || typeof result.order_id !== 'string' || !result.order_id
    || typeof result.order_number !== 'string' || !result.order_number
    || typeof result.status !== 'string' || result.payment_method !== 'cod') {
    throw new Error('The order response was incomplete. Check the order status before retrying.')
  }
  paisa(result.total)
  return result
}
export function safeWhatsapp(value: string | null): string | undefined {
  if (!value) return undefined
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && url.hostname === 'wa.me' && !url.username && !url.password ? url.href : undefined
  } catch { return undefined }
}
export function rejectedBeforeCreation(error: unknown): boolean {
  return error instanceof ApiError && (
    error.status === 422 || ['CHECKOUT_QUOTE_CHANGED', 'CHECKOUT_QUOTE_INVALID'].includes(error.code)
  )
}
export async function checkoutRequest(owner: string, payload: OrderPayload | string): Promise<OrderResult> {
  const account = owner !== 'guest'
  if (account) await refreshSession()
  const recovery = typeof payload === 'string'
  return validateOrder(await request<OrderResult>(`/orders${account ? '' : '/guest'}${recovery ? '/recover' : ''}`, {
    method: 'POST', authenticated: account,
    body: JSON.stringify(recovery ? { checkout_key: payload } : payload),
  }))
}
