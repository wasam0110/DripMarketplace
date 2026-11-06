import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import { validateAdminOrderDetail, type AdminOrderDetail } from './orders'

export interface CODQueueItem { order_id: string; order_number: string; customer_name: string; customer_phone: string; total: string; brand_names: string[]; placed_at: string; expires_at: string; minutes_remaining: number; updated_at: string }
export type CODAction = 'verify' | 'cancel'
const fail = (): never => { throw new Error('COD review information could not be verified. Refresh the queue and inspect the order.') }
const time = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
export function validateCODQueue(value: CODQueueItem[]) {
  if (!Array.isArray(value)) return fail()
  const ids = new Set<string>()
  for (const row of value) {
    if (!row || typeof row.order_id !== 'string' || !isOrderId(row.order_id) || ids.has(row.order_id) || ![row.order_number, row.customer_name].every((v) => typeof v === 'string' && !!v.trim()) || typeof row.customer_phone !== 'string' || typeof row.total !== 'string' || !/^\d{1,12}(\.\d{1,2})?$/.test(row.total) || paisa(row.total) <= 0n || !Array.isArray(row.brand_names) || row.brand_names.some((v) => typeof v !== 'string') || ![row.placed_at, row.expires_at, row.updated_at].every(time) || Date.parse(row.expires_at) <= Date.parse(row.placed_at) || !Number.isSafeInteger(row.minutes_remaining) || row.minutes_remaining < 0) return fail()
    ids.add(row.order_id)
  }
  return value
}
export function matchCODOrder(row: CODQueueItem, order: AdminOrderDetail) {
  validateAdminOrderDetail(order, row.order_id)
  if (order.status !== 'pending_cod_verification' || order.payment_method !== 'cod' || order.order_number !== row.order_number || paisa(order.total) !== paisa(row.total) || Date.parse(order.created_at) !== Date.parse(row.placed_at)) return fail()
  if (order.address && (order.address.recipient_name !== row.customer_name || order.address.phone !== row.customer_phone)) return fail()
  const names = [...new Set(order.seller_orders.map((item) => item.brand_name))].sort()
  if (JSON.stringify(names) !== JSON.stringify([...new Set(row.brand_names)].sort())) return fail()
  return order
}
export function codPayload(action: CODAction, note: string, checked: boolean, row: CODQueueItem, now = Date.now()) {
  const clean = note.trim()
  if (!['verify', 'cancel'].includes(action) || !checked || clean.length > 500 || /[\u0000-\u001f\u007f]/.test(clean)) throw new Error('Confirm the reviewed action and use a note of at most 500 characters without control characters.')
  if (action === 'cancel' && clean.length < 10) throw new Error('Give a cancellation reason of 10–500 characters.')
  if (action === 'verify' && (!row.customer_phone.trim() || now >= Date.parse(row.expires_at))) throw new Error('Approval requires customer contact information and an unexpired COD deadline.')
  return { note: clean || null, expected_updated_at: row.updated_at, expected_expires_at: row.expires_at }
}
export function sameCODReview(before: CODQueueItem, order: AdminOrderDetail, latest: CODQueueItem, current: AdminOrderDetail) {
  const snapshot = (row: CODQueueItem, detail: AdminOrderDetail) => ({ row: { ...row, minutes_remaining: 0, brand_names: [...row.brand_names].sort() }, detail: { ...detail, items: [...detail.items].sort((a, b) => a.id.localeCompare(b.id)), seller_orders: [...detail.seller_orders].sort((a, b) => a.id.localeCompare(b.id)) } })
  return JSON.stringify(snapshot(before, order)) === JSON.stringify(snapshot(latest, current))
}
export function confirmCODReceipt(value: { order_id: string; order_number: string; status: string; message: string }, row: CODQueueItem, action: CODAction) {
  if (!value || value.order_id !== row.order_id || value.order_number !== row.order_number || value.status !== (action === 'verify' ? 'processing' : 'cancelled') || typeof value.message !== 'string') return fail()
  return value
}
export function confirmCODOrder(value: AdminOrderDetail, row: CODQueueItem, action: CODAction, before?: AdminOrderDetail) {
  validateAdminOrderDetail(value, row.order_id)
  if (value.order_number !== row.order_number || value.payment_method !== 'cod' || value.status !== (action === 'verify' ? 'processing' : 'cancelled') || paisa(value.total) !== paisa(row.total) || (action === 'cancel' && value.seller_orders.some((item) => item.status !== 'cancelled'))) return fail()
  const snapshot = (order: AdminOrderDetail) => JSON.stringify([order.user_id, order.order_number, order.created_at, order.subtotal, order.discount_amount, order.shipping_fee, order.total, order.notes, order.address, [...order.items].sort((a, b) => a.id.localeCompare(b.id)), order.seller_orders.map(({ id, seller_id, subtotal }) => ({ id, seller_id, subtotal })).sort((a, b) => a.id.localeCompare(b.id))])
  if (before && snapshot(value) !== snapshot(before)) return fail()
  return value
}
export const codMarker = (owner: string, id: string) => `wearhowz:admin-cod-pending:${owner}:${id}`
