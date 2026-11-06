import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export const paymentStatuses = ['pending', 'processing', 'completed', 'failed', 'refunded'] as const
export function paymentStatusLabel(status: string) {
  switch (status) { case 'pending': return 'Awaiting payment / collection'; case 'processing': return 'Payment processing'; case 'completed': return 'Completed'; case 'failed': return 'Failed'; case 'refunded': return 'Refunded'; default: return 'Status unavailable' }
}
export interface PaymentRow { id: string; order_id: string; order_number: string; method: string; status: string; amount: string; currency: string; gateway_reference: string | null; paid_at: string | null; created_at: string }
export interface AdminPayments { data: PaymentRow[]; total: number; page: number; per_page: number; total_pages: number }
export interface AdminPayment extends PaymentRow { currency: string; order_status: string; order_updated_at: string; can_record_cod_collection: boolean; collection_blockers: string[]; collection_recorded_by: string | null }
export interface CollectionReceipt { payment_id: string; order_id: string; order_number: string; status: string; amount: string; currency: string; reference: string; paid_at: string; recorded_by: string | null }
const fail = (): never => { throw new Error('Payment information could not be verified. Refresh and inspect the saved records.') }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,10}(\.\d{1,2})?$/.test(v) && paisa(v) > 0n
const count = (v: unknown): v is number => Number.isSafeInteger(v) && Number(v) >= 0
export function paymentQuery(status: string, method: string, page: string) {
  if (!(status === 'all' || paymentStatuses.some((v) => v === status)) || !['all', 'cod', 'payfast'].includes(method) || !/^[1-9]\d*$/.test(page) || !Number.isSafeInteger(Number(page))) throw new Error('Choose supported payment filters and a positive page number.')
  const query = new URLSearchParams({ page }); if (status !== 'all') query.set('status', status); if (method !== 'all') query.set('method', method); return query.toString()
}
export function validatePaymentRow(row: PaymentRow) {
  if (!row || ![row.id, row.order_id].every((v) => typeof v === 'string' && isOrderId(v)) || ![row.order_number, row.method, row.status].every(text) || typeof row.currency !== 'string' || !/^[A-Z]{3}$/.test(row.currency) || !money(row.amount) || !date(row.created_at) || !(row.gateway_reference === null || typeof row.gateway_reference === 'string') || !(row.paid_at === null || date(row.paid_at))) return fail()
  return row
}
export function validatePayments(value: AdminPayments, page: number, status: string, method: string) {
  if (!value || !Array.isArray(value.data) || value.page !== page || value.per_page !== 25 || !count(value.total) || value.total_pages !== Math.max(1, Math.ceil(value.total / 25)) || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>(); for (const row of value.data) { validatePaymentRow(row); if (ids.has(row.id) || (status !== 'all' && row.status !== status) || (method !== 'all' && row.method !== method)) return fail(); ids.add(row.id) }; return value
}
export function validatePayment(value: AdminPayment, id: string) {
  validatePaymentRow(value)
  if (value.id !== id || !text(value.currency) || !text(value.order_status) || !date(value.order_updated_at) || typeof value.can_record_cod_collection !== 'boolean' || !Array.isArray(value.collection_blockers) || value.collection_blockers.some((v) => !text(v)) || !(value.collection_recorded_by === null || (typeof value.collection_recorded_by === 'string' && isOrderId(value.collection_recorded_by)))) return fail()
  if (value.can_record_cod_collection !== (value.collection_blockers.length === 0)) return fail()
  if (value.can_record_cod_collection && (value.method !== 'cod' || value.status !== 'pending' || value.currency !== 'PKR' || !['delivered', 'completed'].includes(value.order_status) || value.paid_at !== null || value.gateway_reference !== null || value.collection_recorded_by !== null)) return fail()
  return value
}
export function collectionPayload(payment: AdminPayment, reference: string, checked: boolean) {
  validatePayment(payment, payment.id)
  const clean = reference.trim()
  if (!payment.can_record_cod_collection) throw new Error('This payment is not eligible for collection. Refresh and inspect the saved order.')
  if (!checked || clean.length < 3 || clean.length > 255 || /[\u0000-\u001f\u007f]/.test(clean)) throw new Error('Confirm receipt of the full saved amount and give a reference of 3–255 characters without control characters.')
  return { reference: clean, expected_amount: payment.amount, expected_order_updated_at: payment.order_updated_at }
}
export function samePaymentReview(before: AdminPayment, current: AdminPayment) {
  validatePayment(current, before.id)
  return JSON.stringify(before) === JSON.stringify(current)
}
export function confirmCollection(receipt: CollectionReceipt, before: AdminPayment, reference: string, owner: string) {
  if (!receipt || receipt.payment_id !== before.id || receipt.order_id !== before.order_id || receipt.order_number !== before.order_number || receipt.status !== 'completed' || receipt.currency !== 'PKR' || !money(receipt.amount) || paisa(receipt.amount) !== paisa(before.amount) || receipt.reference !== reference || !date(receipt.paid_at) || receipt.recorded_by !== owner) return fail()
  return receipt
}
export function confirmCollectionReadback(current: AdminPayment, before: AdminPayment, receipt: CollectionReceipt) {
  validatePayment(current, before.id)
  if (current.order_id !== before.order_id || current.order_number !== before.order_number || current.method !== 'cod' || current.currency !== 'PKR' || current.status !== 'completed' || paisa(current.amount) !== paisa(before.amount) || current.created_at !== before.created_at || current.gateway_reference !== receipt.reference || !current.paid_at || Date.parse(current.paid_at) !== Date.parse(receipt.paid_at) || current.collection_recorded_by !== receipt.recorded_by || current.can_record_cod_collection) return fail()
  return current
}
export const collectionMarker = (owner: string, id: string) => `wearhowz:admin-collection-pending:${owner}:${id}`
