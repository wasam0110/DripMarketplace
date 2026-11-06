import { isOrderId, type OrderDetail } from '../orders/api'
import { paisa } from '../checkout/preview'

export const adminOrderStatuses = ['pending_payment', 'payment_confirmed', 'pending_cod_verification', 'processing', 'shipped', 'delivered', 'completed', 'cancelled', 'refunded'] as const
export interface AdminOrderRow { id: string; order_number: string; status: string; customer_name: string; seller_count: number; subtotal: string; total: string; commission: string; payment_method: string; created_at: string }
export interface AdminOrders { data: AdminOrderRow[]; totals: { total_gmv: string; total_commission: string; order_count: number }; total: number; page: number; per_page: number; total_pages: number }
export interface AdminOrderDetail extends OrderDetail { customer_name: string; user_id: string | null; commission: string }
const fail = (): never => { throw new Error('Admin order information could not be verified. Refresh to try again.') }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const uuid = (v: unknown): v is string => typeof v === 'string' && isOrderId(v)
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,24}(\.\d{1,2})?$/.test(v)
const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
const nullable = (v: unknown) => v === null || typeof v === 'string'
export function adminOrderQuery(status: string, method: string, seller: string, page: string) {
  if (!(status === 'all' || adminOrderStatuses.some((value) => value === status)) || !['all', 'cod', 'payfast'].includes(method) || !/^[1-9]\d*$/.test(page) || !Number.isSafeInteger(Number(page))) throw new Error('Choose supported order filters and a positive page number.')
  const id = seller.trim(); if (id && !isOrderId(id)) throw new Error('Enter a valid seller reference or leave it blank.')
  const query = new URLSearchParams({ page, per_page: '25' }); if (status !== 'all') query.set('status', status); if (method !== 'all') query.set('payment_method', method); if (id) query.set('seller_id', id); return query.toString()
}
export function paymentMethodLabel(value: string) {
  switch (value) { case 'cod': return 'Cash on delivery'; case 'payfast': return 'PayFast'; case 'card': return 'Card (historical)'; case 'jazzcash': return 'JazzCash (historical)'; case 'easypaisa': return 'Easypaisa (historical)'; default: return 'Method unavailable' }
}
export function validateAdminOrderRow(row: AdminOrderRow) {
  if (!row || !uuid(row.id) || ![row.order_number, row.status, row.payment_method, row.customer_name].every(text) || !count(row.seller_count) || ![row.subtotal, row.total, row.commission].every(money) || !date(row.created_at)) return fail(); return row
}
export function validateAdminOrders(value: AdminOrders, page: number, status: string, method: string) {
  if (!value || !Array.isArray(value.data) || value.page !== page || value.per_page !== 25 || !count(value.total) || value.total_pages !== Math.max(1, Math.ceil(value.total / 25)) || value.data.length > 25 || value.data.length > value.total || !value.totals || value.totals.order_count !== value.total || ![value.totals.total_gmv, value.totals.total_commission].every(money)) return fail()
  const ids = new Set<string>(); for (const row of value.data) { validateAdminOrderRow(row); if (ids.has(row.id) || (status !== 'all' && row.status !== status) || (method !== 'all' && row.payment_method !== method)) return fail(); ids.add(row.id) }; return value
}
export function validateAdminOrderDetail(value: AdminOrderDetail, id: string) {
  if (!value || value.id !== id || !uuid(value.id) || ![value.order_number, value.status, value.payment_method, value.customer_name].every(text) || !(value.user_id === null || uuid(value.user_id)) || ![value.subtotal, value.discount_amount, value.shipping_fee, value.total, value.commission].every(money) || !date(value.created_at) || !nullable(value.notes) || !Array.isArray(value.items) || !Array.isArray(value.seller_orders)) return fail()
  if (value.address !== null && (!value.address || ![value.address.recipient_name, value.address.phone, value.address.street, value.address.city, value.address.province].every((v) => typeof v === 'string') || !nullable(value.address.note))) return fail()
  const items = new Set<string>(), shipments = new Set<string>()
  for (const item of value.items) { if (!item || ![item.id, item.seller_id, item.product_id, item.variant_id].every(uuid) || items.has(item.id) || !text(item.product_name) || typeof item.variant_label !== 'string' || !count(item.quantity) || item.quantity < 1 || ![item.unit_price, item.subtotal].every(money)) return fail(); items.add(item.id) }
  for (const row of value.seller_orders) { if (!row || !uuid(row.id) || shipments.has(row.id) || !uuid(row.seller_id) || typeof row.brand_name !== 'string' || !text(row.status) || !money(row.subtotal) || ![row.tracking_number, row.courier_name].every(nullable) || ![row.shipped_at, row.delivered_at].every((v) => v === null || date(v))) return fail(); shipments.add(row.id) }
  return value
}
/** Expose inconsistent historical snapshots for investigation; never repair on read. */
export function adminOrderWarnings(order: AdminOrderDetail) {
  const messages: string[] = []
  if (!order.address || ![order.address.recipient_name, order.address.phone, order.address.street, order.address.city, order.address.province].every(text)) messages.push('The saved delivery address is missing or incomplete.')
  if (!order.items.length) messages.push('No saved order items are available.')
  if (!order.seller_orders.length) messages.push('No saved brand fulfilment records are available.')
  if (paisa(order.subtotal) - paisa(order.discount_amount) + paisa(order.shipping_fee) !== paisa(order.total)) messages.push('Saved checkout amounts do not reconcile. Investigate before any financial action.')
  if (order.items.length && (order.items.some((item) => paisa(item.unit_price) * BigInt(item.quantity) !== paisa(item.subtotal)) || order.items.reduce((sum, item) => sum + paisa(item.subtotal), 0n) !== paisa(order.subtotal))) messages.push('Saved item amounts do not reconcile with the order subtotal.')
  if (order.seller_orders.length && order.seller_orders.reduce((sum, row) => sum + paisa(row.subtotal), 0n) !== paisa(order.subtotal)) messages.push('Saved brand subtotals do not reconcile with the order subtotal.')
  if (order.items.some((item) => !order.seller_orders.some((row) => row.seller_id === item.seller_id))) messages.push('An item has no matching brand fulfilment record.')
  return messages
}
