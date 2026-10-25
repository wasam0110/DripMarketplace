import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export interface PaymentStatus {
  order_id: string; payment_id: string; status: string; method: string
  amount: string; gateway_reference: string | null; paid_at: string | null
}
export function validatePaymentStatus(value: PaymentStatus, id: string): PaymentStatus {
  if (!value || value.order_id !== id || !isOrderId(value.payment_id)
    || typeof value.status !== 'string' || !value.status
    || typeof value.method !== 'string' || !value.method
    || typeof value.amount !== 'string'
    || !(value.gateway_reference === null || typeof value.gateway_reference === 'string')
    || !(value.paid_at === null || typeof value.paid_at === 'string' && Number.isFinite(Date.parse(value.paid_at)))) {
    throw new Error('The payment status could not be verified. Refresh or contact support.')
  }
  paisa(value.amount)
  return value
}
const statuses: Record<string, { label: string; detail: string }> = {
  pending: { label: 'Payment pending', detail: 'The backend has not confirmed payment. Do not pay again while the outcome is unresolved.' },
  processing: { label: 'Payment processing', detail: 'Payment is still processing. Refresh later; do not start another payment.' },
  completed: { label: 'Payment recorded', detail: 'The backend records this payment as completed. Check the order separately for fulfilment.' },
  failed: { label: 'Payment failed', detail: 'The backend records this payment as failed. If you were charged, contact support before attempting another payment.' },
  refunded: { label: 'Payment refunded', detail: 'The backend records this payment as refunded. This screen is not a bank receipt and does not show refund timing or allocation.' },
}
export const paymentStatusText = (status: string) => Object.hasOwn(statuses, status) ? statuses[status] : {
  label: 'Payment status unavailable', detail: 'This status is not recognised. Contact support before paying again.',
}
