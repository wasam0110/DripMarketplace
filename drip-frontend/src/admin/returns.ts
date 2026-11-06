import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import { type ReturnRow } from '../orders/returnHistory'
import { validateSellerReturn, type SellerReturnItem } from '../seller/returns'
import { canMessage, validateDispute, type DisputeDetail } from '../orders/disputes'

export const returnStates = ['requested', 'approved', 'rejected', 'received', 'refunded']
export const disputeStates = ['open', 'under_review', 'resolved_customer', 'resolved_seller', 'closed']
export type ReturnAction = 'approve' | 'reject' | 'mark_received' | 'request_refund'
export interface AdminReturn extends ReturnRow {
  notes: string | null; items: SellerReturnItem[]; estimated_refund_amount: string; available_actions: string[]
  customer: { user_id: string | null; is_guest: boolean; email: string; first_name: string | null; last_name: string | null; phone: string | null }
  seller: { seller_id: string; brand_name: string }
  order: { order_id: string; order_number: string; status: string; payment_method: string; subtotal: string; discount_amount: string; shipping_fee: string; total: string; payment_id: string | null; payment_status: string | null; payment_currency: string | null }
  refund: { refund_id: string; status: string; amount: string; transfer_reference: string | null; requested_at: string; processed_at: string | null } | null
  dispute: { dispute_id: string; status: string } | null
}
const nullableText = (v: unknown) => v === null || typeof v === 'string'
const nullableId = (v: unknown) => v === null || typeof v === 'string' && isOrderId(v)
const money = (v: unknown) => typeof v === 'string' && /^\d{1,12}(\.\d{1,2})?$/.test(v)
const date = (v: unknown) => typeof v === 'string' && Number.isFinite(Date.parse(v))
function valid(v: unknown): asserts v { if (!v) throw new Error('Admin return or dispute records could not be verified. Refresh before making changes.') }
export function validateAdminReturn(v: AdminReturn, id: string) {
  valid(v && v.order && v.customer && v.seller)
  validateSellerReturn({ ...v, order_number: v.order.order_number, refund_status: v.refund?.status ?? null, dispute_status: v.dispute?.status ?? null }, id)
  valid(v.order.order_id === v.order_id && returnStates.includes(v.status) && typeof v.order.status === 'string'
    && typeof v.order.payment_method === 'string' && nullableId(v.order.payment_id) && nullableText(v.order.payment_status)
    && (v.order.payment_currency === null || /^[A-Z]{3}$/.test(v.order.payment_currency))
    && [v.order.subtotal, v.order.discount_amount, v.order.shipping_fee, v.order.total].every(money)
    && isOrderId(v.seller.seller_id) && typeof v.seller.brand_name === 'string'
    && nullableId(v.customer.user_id) && typeof v.customer.is_guest === 'boolean'
    && typeof v.customer.email === 'string' && [v.customer.first_name, v.customer.last_name, v.customer.phone].every(nullableText))
  if (v.refund) valid(isOrderId(v.refund.refund_id) && ['pending', 'completed'].includes(v.refund.status) && money(v.refund.amount)
    && nullableText(v.refund.transfer_reference) && date(v.refund.requested_at) && (v.refund.processed_at === null || date(v.refund.processed_at)))
  if (v.dispute) valid(isOrderId(v.dispute.dispute_id) && disputeStates.includes(v.dispute.status))
  return v
}
export function returnActions(v: AdminReturn): ReturnAction[] {
  const allowed: ReturnAction[] = v.status === 'requested' ? ['approve', 'reject'] : v.status === 'approved' ? ['mark_received']
    : v.status === 'received' && !v.refund && v.order.payment_status === 'completed' && v.order.payment_currency === 'PKR' && paisa(v.estimated_refund_amount) > 0n ? ['request_refund'] : []
  return allowed.filter(a => v.available_actions.includes(a))
}
export function returnPayload(v: AdminReturn, action: ReturnAction, note: string, checked: boolean) {
  valid(returnActions(v).includes(action))
  if (!checked) throw new Error('Confirm that you reviewed this action first.')
  const text = note.trim()
  if (text.length > 500 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text) || action === 'request_refund' && text.length > 0 && text.length < 5) throw new Error('Use a valid note of up to 500 characters; refund notes need at least 5.')
  return { expected_status: v.status, expected_notes: v.notes, ...(text ? { admin_note: text } : {}), ...(action === 'request_refund' ? { expected_refund_amount: v.estimated_refund_amount } : {}) }
}
export const actionLabel = (a: ReturnAction) => ({ approve: 'Approve return', reject: 'Reject return', mark_received: 'Mark items received', request_refund: 'Request linked refund' })[a]
export const actionPath = (a: ReturnAction) => ({ approve: 'approve', reject: 'reject', mark_received: 'received', request_refund: 'refund' })[a]
export const actionTarget = (a: ReturnAction) => ({ approve: 'approved', reject: 'rejected', mark_received: 'received', request_refund: 'received' })[a]
export function confirmReturn(saved: AdminReturn, before: AdminReturn, action: ReturnAction, body: ReturnType<typeof returnPayload>, receipt: unknown) {
  validateAdminReturn(saved, before.id)
  valid(saved.order_id === before.order_id && saved.seller_order_id === before.seller_order_id && saved.status === actionTarget(action)
    && JSON.stringify(saved.items) === JSON.stringify(before.items))
  if (action === 'request_refund') {
    const r = receipt as { refund_id?: string; status?: string }
    valid(r && r.status === 'pending' && saved.refund && saved.refund.status === 'pending' && saved.refund.refund_id === r.refund_id
      && paisa(saved.refund.amount) === paisa(before.estimated_refund_amount))
  } else valid(saved.notes === (body.admin_note ?? before.notes))
  return saved
}
export function validateAdminDispute(v: DisputeDetail, id: string) {
  valid(v && v.id === id && isOrderId(v.return_id) && disputeStates.includes(v.status))
  validateDispute(v, v.return_id)
  valid(canMessage(v.status) ? v.resolved_at === null : v.status === 'closed' || v.resolved_at !== null)
  return v
}
export interface DisputeList { data: DisputeDetail[]; total: number; page: number }
export function validateDisputes(v: DisputeList, page: number, filter: string) {
  valid(v && Array.isArray(v.data) && Number.isSafeInteger(v.total) && v.total >= 0 && v.page === page && v.data.length <= 25 && v.data.length <= v.total)
  const ids = new Set<string>()
  for (const row of v.data) { validateAdminDispute(row, row.id); valid(!ids.has(row.id) && (!filter || row.status === filter)); ids.add(row.id) }
  return v
}
export function disputePayload(v: DisputeDetail, kind: 'message' | 'customer' | 'seller', text: string, checked: boolean): { expected_status: string; expected_message_count: number; body?: string; in_favor_of?: 'customer' | 'seller'; resolution_note?: string } {
  valid(canMessage(v.status))
  const value = text.trim(), min = kind === 'message' ? 1 : 10, max = kind === 'message' ? 2000 : 1000
  if (!checked || value.length < min || value.length > max || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) throw new Error(`Review the action and enter ${min}–${max} characters.`)
  return { expected_status: v.status, expected_message_count: v.messages.length, ...(kind === 'message' ? { body: value } : { in_favor_of: kind, resolution_note: value }) }
}
export const returnMarker = (owner: string, kind: string, id: string) => `wearhowz:admin-${kind}-pending:${owner}:${id}`
