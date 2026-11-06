import { paisa } from '../checkout/preview'
import { isOrderId } from '../orders/api'

export interface Allocation { seller_order_id: string; seller_id: string; merchandise_amount: string; commission_rate: string | null; commission_reversal_amount: string; seller_reversal_amount: string; recovered_amount: string; settlement_offset_amount: string; platform_shortfall_amount: string; reconciled: boolean }
export interface RefundAccounting { merchandise_amount: string; shipping_amount: string; commission_reversal_amount: string; seller_reversal_amount: string; recovered_amount: string; settlement_offset_amount: string; platform_shortfall_amount: string; platform_funded_amount: string; reconciled: boolean; allocations: Allocation[] }
export interface RefundRow { refund_id: string; payment_id: string; order_id: string; order_number: string; return_id: string | null; status: 'pending' | 'completed'; amount: string; currency: string; reason: string; transfer_reference: string | null; requested_by: string | null; confirmed_by: string | null; requested_at: string; processed_at: string | null; accounting: RefundAccounting | null }
export interface Refunds { data: RefundRow[]; total: number; page: number; per_page: number; total_pages: number }
export interface RefundBalance { payment_id: string; order_id: string; order_number: string; payment_status: string; payment_method: string; payment_amount: string; currency: string; pending_refund_amount: string; completed_refund_amount: string; reserved_refund_amount: string; remaining_refundable_amount: string; can_request_refund: boolean }
export interface RefundHistory extends RefundBalance { refunds: RefundRow[] }
export interface RefundDetail extends RefundRow { payment: RefundBalance; history: { event: 'requested' | 'completed'; occurred_at: string; actor_id: string | null; transfer_reference: string | null }[]; can_confirm_refund: boolean; confirmation_blockers: string[]; linked_return_status: string | null }
export interface RefundReceipt { refund_id: string; payment_id: string; amount: string; reason: string; gateway_ref: string | null; created_at: string; status: string; processed_at: string | null }
const fail = (): never => { throw new Error('Refund information could not be verified. Refresh and inspect the saved records.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && isOrderId(v)
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const nullable = (v: unknown) => v === null || typeof v === 'string'
const actor = (v: unknown) => v === null || uuid(v)
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,12}(\.\d{1,2})?$/.test(v)
const count = (v: unknown): v is number => Number.isSafeInteger(v) && Number(v) >= 0
const amounts = ['commission_reversal_amount', 'seller_reversal_amount', 'recovered_amount', 'settlement_offset_amount', 'platform_shortfall_amount'] as const
export function refundQuery(status: string, payment: string, page: string) {
  if (!['all', 'pending', 'completed'].includes(status) || !/^[1-9]\d*$/.test(page) || !Number.isSafeInteger(Number(page)) || (payment.trim() && !uuid(payment.trim()))) throw new Error('Choose supported refund filters, a valid optional payment reference and a positive page.')
  const query = new URLSearchParams({ page }); if (status !== 'all') query.set('status', status); if (payment.trim()) query.set('payment_id', payment.trim()); return query.toString()
}
function accounting(value: RefundAccounting, amount: string) {
  if (!value || ![value.merchandise_amount, value.shipping_amount, value.platform_funded_amount, ...amounts.map((key) => value[key])].every(money) || typeof value.reconciled !== 'boolean' || !Array.isArray(value.allocations) || paisa(value.merchandise_amount) + paisa(value.shipping_amount) !== paisa(amount)) return fail()
  const ids = new Set<string>()
  for (const row of value.allocations) {
    if (!row || !uuid(row.seller_order_id) || !uuid(row.seller_id) || ids.has(row.seller_order_id) || ![row.merchandise_amount, ...amounts.map((key) => row[key])].every(money) || typeof row.reconciled !== 'boolean' || !(row.commission_rate === null || (typeof row.commission_rate === 'string' && /^(0(\.\d{1,6})?|1(\.0{1,6})?)$/.test(row.commission_rate)))) return fail()
    if (paisa(row.recovered_amount) + paisa(row.settlement_offset_amount) + paisa(row.platform_shortfall_amount) !== paisa(row.seller_reversal_amount)) return fail()
    if (row.reconciled && paisa(row.commission_reversal_amount) + paisa(row.seller_reversal_amount) !== paisa(row.merchandise_amount)) return fail()
    ids.add(row.seller_order_id)
  }
  for (const key of [...amounts, 'merchandise_amount'] as const) if (value.allocations.reduce((sum, row) => sum + paisa(row[key]), 0n) !== paisa(value[key])) return fail()
  if (paisa(value.platform_funded_amount) !== paisa(value.shipping_amount) + paisa(value.commission_reversal_amount) + paisa(value.platform_shortfall_amount) || value.reconciled !== value.allocations.every((row) => row.reconciled)) return fail()
  return value
}
export function validateRefundRow(row: RefundRow) {
  if (!row || ![row.refund_id, row.payment_id, row.order_id].every(uuid) || !text(row.order_number) || !actor(row.return_id) || !['pending', 'completed'].includes(row.status) || !money(row.amount) || paisa(row.amount) <= 0n || typeof row.currency !== 'string' || !/^[A-Z]{3}$/.test(row.currency) || typeof row.reason !== 'string' || !nullable(row.transfer_reference) || !actor(row.requested_by) || !actor(row.confirmed_by) || !date(row.requested_at) || !(row.processed_at === null || date(row.processed_at)) || (row.status === 'completed') !== (row.processed_at !== null)) return fail()
  if (row.accounting !== null) accounting(row.accounting, row.amount)
  return row
}
export function validateRefunds(value: Refunds, page: number, status: string, payment: string) {
  if (!value || !Array.isArray(value.data) || value.page !== page || value.per_page !== 25 || !count(value.total) || value.total_pages !== Math.max(1, Math.ceil(value.total / 25)) || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>(); for (const row of value.data) { validateRefundRow(row); if (ids.has(row.refund_id) || (status !== 'all' && row.status !== status) || (payment && row.payment_id !== payment)) return fail(); ids.add(row.refund_id) }; return value
}
export function validateBalance(value: RefundBalance, id: string) {
  if (!value || value.payment_id !== id || !uuid(id) || !uuid(value.order_id) || ![value.order_number, value.payment_status, value.payment_method].every(text) || !/^[A-Z]{3}$/.test(value.currency) || ![value.payment_amount, value.pending_refund_amount, value.completed_refund_amount, value.reserved_refund_amount, value.remaining_refundable_amount].every(money) || paisa(value.payment_amount) <= 0n || typeof value.can_request_refund !== 'boolean') return fail()
  const reserved = paisa(value.pending_refund_amount) + paisa(value.completed_refund_amount), left = paisa(value.payment_amount) - reserved
  if (reserved !== paisa(value.reserved_refund_amount) || paisa(value.remaining_refundable_amount) !== (left > 0n ? left : 0n) || value.can_request_refund !== (value.currency === 'PKR' && value.payment_status === 'completed' && left > 0n)) return fail()
  return value
}
function samePayment(row: RefundRow, balance: RefundBalance) { if (row.payment_id !== balance.payment_id || row.order_id !== balance.order_id || row.order_number !== balance.order_number || row.currency !== balance.currency) return fail() }
export function validateRefundHistory(value: RefundHistory, id: string) {
  validateBalance(value, id); if (!Array.isArray(value.refunds)) return fail()
  const ids = new Set<string>(); let pending = 0n, completed = 0n
  for (const row of value.refunds) { validateRefundRow(row); samePayment(row, value); if (ids.has(row.refund_id)) return fail(); ids.add(row.refund_id); if (row.status === 'pending') pending += paisa(row.amount); else completed += paisa(row.amount) }
  if (pending !== paisa(value.pending_refund_amount) || completed !== paisa(value.completed_refund_amount)) return fail()
  return value
}
export function validateRefundDetail(value: RefundDetail, id: string) {
  validateRefundRow(value); if (value.refund_id !== id) return fail(); validateBalance(value.payment, value.payment_id); samePayment(value, value.payment)
  if (paisa(value.amount) > paisa(value.status === 'pending' ? value.payment.pending_refund_amount : value.payment.completed_refund_amount)) return fail()
  if (!Array.isArray(value.history) || value.history.length !== (value.status === 'pending' ? 1 : 2) || typeof value.can_confirm_refund !== 'boolean' || !Array.isArray(value.confirmation_blockers) || value.confirmation_blockers.some((v) => !text(v)) || !nullable(value.linked_return_status) || value.can_confirm_refund !== (value.confirmation_blockers.length === 0)) return fail()
  const requested = value.history[0], completed = value.history[1]
  if (!requested || requested.event !== 'requested' || requested.occurred_at !== value.requested_at || requested.actor_id !== value.requested_by || (value.status === 'completed' && (!completed || completed.event !== 'completed' || completed.occurred_at !== value.processed_at || completed.actor_id !== value.confirmed_by || completed.transfer_reference !== value.transfer_reference))) return fail()
  if (value.can_confirm_refund && (value.status !== 'pending' || value.currency !== 'PKR' || value.payment.payment_status !== 'completed' || value.transfer_reference !== null || value.confirmed_by !== null || (value.return_id !== null && value.linked_return_status !== 'received'))) return fail()
  return value
}
export function refundRequestPayload(balance: RefundHistory, amount: string, reason: string, checked: boolean, key: string) {
  validateRefundHistory(balance, balance.payment_id); const clean = reason.trim()
  if (!balance.can_request_refund || !money(amount) || paisa(amount) <= 0n || paisa(amount) > paisa(balance.remaining_refundable_amount) || !checked || clean.length < 5 || clean.length > 500 || /[\u0000-\u001f\u007f]/.test(clean) || !uuid(key)) throw new Error('Confirm the pending direct-refund request, choose an amount within the remaining balance, and give a reason of 5–500 characters without control characters.')
  return { amount, reason: clean, idempotency_key: key, expected_remaining_amount: balance.remaining_refundable_amount }
}
export function refundConfirmPayload(detail: RefundDetail, reference: string, checked: boolean) {
  validateRefundDetail(detail, detail.refund_id); const clean = reference.trim()
  if (!detail.can_confirm_refund || !checked || clean.length < 3 || clean.length > 255 || /[\u0000-\u001f\u007f]/.test(clean)) throw new Error('Confirm the actual transfer and use its reference of 3–255 characters without control characters.')
  return { reference: clean, expected_amount: detail.amount, expected_payment_id: detail.payment_id, expected_return_id: detail.return_id }
}
export function refundReceipt(value: RefundReceipt, payment: string, amount: string, reason: string, status: string, id?: string, reference?: string) {
  if (!value || !uuid(value.refund_id) || (id && value.refund_id !== id) || value.payment_id !== payment || !money(value.amount) || paisa(value.amount) !== paisa(amount) || value.reason !== reason || value.status !== status || !date(value.created_at) || (status === 'pending' ? value.gateway_ref !== null || value.processed_at !== null : value.gateway_ref !== reference || !date(value.processed_at))) return fail()
  return value
}
export const refundMarker = (owner: string, kind: 'request' | 'confirm', id: string) => `wearhowz:admin-refund-${kind}-pending:${owner}:${id}`
