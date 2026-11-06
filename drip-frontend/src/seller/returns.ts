import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import { validateReturnRow, type ReturnList, type ReturnRow } from '../orders/returnHistory'

export type SellerReturnAction = 'approve' | 'reject' | 'mark_received'
export interface SellerReturnItem {
  id: string; order_item_id: string; product_id: string; variant_id: string; product_name: string; variant_label: string
  unit_price: string; purchased_quantity: number; requested_quantity: number; line_subtotal: string; reason: string | null
}
export interface SellerReturnDetail extends ReturnRow {
  notes: string | null; order_number: string; items: SellerReturnItem[]; estimated_refund_amount: string
  available_actions: string[]; refund_status: string | null; dispute_status: string | null
}
const nullableText = (v: unknown) => v === null || typeof v === 'string'
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,12}(\.\d{1,2})?$/.test(v)
const fail = () => { throw new Error('The seller return details could not be verified. Refresh to try again.') }
export function validateSellerReturns(value: ReturnList, page: number, filter: string) {
  if (!value || !Array.isArray(value.data) || !Number.isSafeInteger(value.total) || value.total < 0
    || value.page !== page || value.total_pages !== Math.max(1, Math.ceil(value.total / 25))
    || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateReturnRow(row); if (ids.has(row.id) || (filter && row.status !== filter)) return fail(); ids.add(row.id) }
  return value
}
export function validateSellerReturn(value: SellerReturnDetail, id: string) {
  validateReturnRow(value)
  if (value.id !== id || !nullableText(value.notes) || typeof value.order_number !== 'string' || !value.order_number.trim()
    || !Array.isArray(value.items) || value.items.length !== value.item_count || !money(value.estimated_refund_amount)
    || !nullableText(value.refund_status) || !nullableText(value.dispute_status)
    || !Array.isArray(value.available_actions) || value.available_actions.some((v) => typeof v !== 'string')
    || new Set(value.available_actions).size !== value.available_actions.length) return fail()
  const ids = new Set<string>(), orderItems = new Set<string>()
  let total = 0n
  for (const row of value.items) {
    if (!row || ![row.id, row.order_item_id, row.product_id, row.variant_id].every((v) => typeof v === 'string' && isOrderId(v))
      || ids.has(row.id) || orderItems.has(row.order_item_id) || typeof row.product_name !== 'string' || !row.product_name.trim()
      || typeof row.variant_label !== 'string' || !money(row.unit_price) || !money(row.line_subtotal)
      || !Number.isSafeInteger(row.purchased_quantity) || !Number.isSafeInteger(row.requested_quantity)
      || row.requested_quantity < 1 || row.purchased_quantity < row.requested_quantity || !nullableText(row.reason)
      || paisa(row.unit_price) * BigInt(row.requested_quantity) !== paisa(row.line_subtotal)) return fail()
    ids.add(row.id); orderItems.add(row.order_item_id); total += paisa(row.line_subtotal)
  }
  if (paisa(value.estimated_refund_amount) > total) return fail()
  return value
}
export function sellerReturnActions(value: Pick<SellerReturnDetail, 'status' | 'available_actions'>): SellerReturnAction[] {
  const allowed: SellerReturnAction[] = value.status === 'requested' ? ['approve', 'reject'] : value.status === 'approved' ? ['mark_received'] : []
  return allowed.filter((action) => value.available_actions.includes(action))
}
export function sellerReturnBody(action: SellerReturnAction, note: string, value: SellerReturnDetail): { admin_note?: string } {
  if (!sellerReturnActions(value).includes(action)) throw new Error('This action is no longer available. Refresh the return.')
  const text = note.trim()
  if (text.length > 500) throw new Error('Use a decision note of 500 characters or fewer.')
  return text ? { admin_note: text } : {}
}
export function sellerReturnTarget(action: SellerReturnAction) { return action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'received' }
export function confirmSellerReturn(value: SellerReturnDetail, before: SellerReturnDetail, action: SellerReturnAction, body: { admin_note?: string }) {
  validateSellerReturn(value, before.id)
  if (value.order_id !== before.order_id || value.seller_order_id !== before.seller_order_id || value.status !== sellerReturnTarget(action)
    || (body.admin_note !== undefined && value.notes !== body.admin_note)
    || value.items.length !== before.items.length || !before.items.every((item) => value.items.some((saved) => saved.id === item.id && saved.order_item_id === item.order_item_id && saved.requested_quantity === item.requested_quantity))) return fail()
  return value
}
export function sellerReturnLabel(status: string) {
  switch (status) { case 'requested': return 'Awaiting review'; case 'approved': return 'Approved'; case 'rejected': return 'Rejected'; case 'received': return 'Items received'; case 'refunded': return 'Refunded'; default: return 'Status unavailable' }
}
export const sellerReturnMarker = (owner: string, id: string) => `wearhowz:seller-return-pending:${owner}:${id}`
