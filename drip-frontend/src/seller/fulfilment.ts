import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export interface FulfilmentRow {
  id: string; order_id: string; order_number: string; status: string; subtotal: string
  tracking_number: string | null; courier_name: string | null; shipped_at: string | null; delivered_at: string | null; created_at: string
}
export interface FulfilmentPage { data: FulfilmentRow[]; pagination: { page: number; per_page: number; total: number; total_pages: number } }
export interface FulfilmentDetail extends FulfilmentRow {
  shipping_address: { recipient_name: string; phone: string; street: string; city: string; province: string; note: string | null }
  items: { product_name: string; variant_label: string; unit_price: string; quantity: number; subtotal: string }[]
}
export interface FulfilmentChange { status: 'processing' | 'shipped' | 'delivered'; tracking_number?: string; courier_name?: string }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const integer = (v: unknown, minimum: number) => Number.isSafeInteger(v) && Number(v) >= minimum
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,12}(\.\d{1,2})?$/.test(v)
const time = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v) && Number.isFinite(Date.parse(v))
const fail = () => { throw new Error('The fulfilment order could not be verified. Refresh to try again.') }
export function validateFulfilmentRow(row: FulfilmentRow) {
  if (!row || typeof row.id !== 'string' || !isOrderId(row.id) || typeof row.order_id !== 'string' || !isOrderId(row.order_id)
    || !text(row.order_number) || !text(row.status) || !money(row.subtotal) || !time(row.created_at)
    || ![row.tracking_number, row.courier_name].every((v) => v === null || typeof v === 'string')
    || ![row.shipped_at, row.delivered_at].every((v) => v === null || time(v))) return fail()
  return row
}
export function validateFulfilmentPage(value: FulfilmentPage, page: number, filter: string) {
  const p = value?.pagination
  if (!value || !Array.isArray(value.data) || !p || p.page !== page || p.per_page !== 25 || !integer(p.total, 0)
    || p.total_pages !== Math.max(1, Math.ceil(p.total / 25)) || value.data.length > 25 || value.data.length > p.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateFulfilmentRow(row); if (ids.has(row.id) || (filter !== 'all' && row.status !== filter)) return fail(); ids.add(row.id) }
  return value
}
export function validateFulfilmentDetail(value: FulfilmentDetail, id: string, orderId?: string) {
  validateFulfilmentRow(value)
  if (value.id !== id || (orderId && value.order_id !== orderId) || !value.shipping_address || !Array.isArray(value.items) || !value.items.length) return fail()
  const address = value.shipping_address
  if (![address.recipient_name, address.phone, address.street, address.city, address.province].every((v) => typeof v === 'string') || !(address.note === null || typeof address.note === 'string')) return fail()
  let total = 0n
  for (const item of value.items) {
    if (!item || !text(item.product_name) || typeof item.variant_label !== 'string' || !integer(item.quantity, 1) || !money(item.unit_price) || !money(item.subtotal)) return fail()
    if (paisa(item.unit_price) * BigInt(item.quantity) !== paisa(item.subtotal)) return fail()
    total += paisa(item.subtotal)
  }
  if (total !== paisa(value.subtotal)) return fail()
  return value
}
export function nextFulfilment(status: string): FulfilmentChange['status'] | null {
  switch (status) { case 'pending': return 'processing'; case 'processing': return 'shipped'; case 'shipped': return 'delivered'; default: return null }
}
export function completeShippingAddress(value: FulfilmentDetail['shipping_address']) {
  return [value.recipient_name, value.phone, value.street, value.city, value.province].every(text)
}
export function fulfilmentChange(before: FulfilmentDetail, tracking: string, courier: string): FulfilmentChange {
  const status = nextFulfilment(before.status)
  if (!status) throw new Error('No fulfilment action is available for this order.')
  if (status !== 'shipped') return { status }
  const number = tracking.trim(), name = courier.trim()
  if (!number || number.length > 100 || name.length > 100 || /[\x00-\x1f\x7f]/.test(number + name)) throw new Error('Enter a tracking number of 1–100 characters and an optional courier name up to 100 characters.')
  return { status, tracking_number: number, ...(name ? { courier_name: name } : {}) }
}
export function confirmFulfilment(value: FulfilmentDetail, before: FulfilmentDetail, change: FulfilmentChange) {
  validateFulfilmentDetail(value, before.id, before.order_id)
  if (value.status !== change.status || (change.tracking_number !== undefined && value.tracking_number !== change.tracking_number)
    || (change.courier_name !== undefined && value.courier_name !== change.courier_name)) return fail()
  return value
}
export function fulfilmentLabel(status: string) {
  switch (status) { case 'pending': return 'Awaiting preparation'; case 'processing': return 'Preparing'; case 'shipped': return 'Shipped'; case 'delivered': return 'Delivered'; case 'cancelled': return 'Cancelled'; default: return 'Status unavailable' }
}
export const fulfilmentMarker = (owner: string, id: string) => `wearhowz:fulfilment-pending:${owner}:${id}`
