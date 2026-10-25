import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import type { OrderResult } from '../checkout/submission'

export const payfastEnabled = import.meta.env.VITE_ENABLE_PAYFAST === 'true'
export const payfastEndpoint = `https://${import.meta.env.VITE_PAYFAST_ENVIRONMENT === 'live' ? 'ipg1' : 'ipguat'}.apps.net.pk/Ecommerce/api/Transaction/PostTransaction`
export interface PayFastHandoff { payment_id: string; attempt_id: string; method: string; checkout_url: string; payfast_payload: Record<string, string>; expires_at?: string | null }
const fields = ['MERCHANT_ID', 'MERCHANT_NAME', 'TOKEN', 'PROCCODE', 'TXNAMT', 'CUSTOMER_MOBILE_NO', 'CUSTOMER_EMAIL_ADDRESS', 'SIGNATURE', 'VERSION', 'TXNDESC', 'SUCCESS_URL', 'FAILURE_URL', 'BASKET_ID', 'ORDER_DATE', 'CHECKOUT_URL', 'CURRENCY_CODE']
export function validateHandoff(value: PayFastHandoff, order: OrderResult, origin: string, callbackOrigin: string): PayFastHandoff {
  const fail = () => { throw new Error('The payment handoff could not be verified. Check payment status before doing anything else.') }
  if (!value || value.method !== 'payfast' || !isOrderId(value.payment_id) || typeof value.attempt_id !== 'string' || !isOrderId(value.attempt_id) || value.checkout_url !== payfastEndpoint || !value.payfast_payload) return fail()
  const payload = value.payfast_payload
  if (Object.keys(payload).length !== fields.length || fields.some((key) => typeof payload[key] !== 'string' || !payload[key] || payload[key].length > 8192)) return fail()
  if (payload.BASKET_ID !== value.attempt_id || payload.CURRENCY_CODE !== 'PKR' || payload.PROCCODE !== '00'
    || paisa(payload.TXNAMT) !== paisa(order.total) || paisa(order.total) <= 0n
    || payload.SUCCESS_URL !== `${origin}/order/success/${order.order_id}`
    || payload.FAILURE_URL !== `${origin}/payments/${order.order_id}?payment=failed`
    || payload.CHECKOUT_URL !== `${callbackOrigin}/api/v1/payments/callback/payfast`) return fail()
  if (value.expires_at != null && (!Number.isFinite(Date.parse(value.expires_at)) || Date.parse(value.expires_at) <= Date.now())) return fail()
  return value
}
export const paymentAttemptKey = (id: string) => `wearhowz.payfast-attempt.v1:${id}`
