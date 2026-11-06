import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export const sellerStatuses = ['pending_payment', 'pending_approval', 'active', 'suspended', 'rejected'] as const
export type SellerDecision = 'approve' | 'reject' | 'suspend' | 'reinstate'
export interface AdminSeller {
  id: string; brand_name: string; status: string; slots_used: number; total_slots: number; product_count: number
  total_gmv: string; platform_cut: string; available_balance: string; joined_at: string
}
export interface AdminSellerDetail extends AdminSeller {
  slug: string; description: string | null; whatsapp_number: string | null; instagram_handle: string | null
  logo_url: string | null; return_policy: string | null; pending_balance: string; registration_fee: string; rejected_reason: string | null
  registration_amount_due: string; registration_paid_at: string | null; registration_payment_reference: string | null; registration_paid_by: string | null
}
export interface AdminSellerPage { data: AdminSeller[]; total: number; page: number; per_page: number; total_pages: number }
const fail = (): never => { throw new Error('Seller review information could not be verified. Refresh to try again.') }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,24}(\.\d{1,2})?$/.test(v)
const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0
const nullableText = (v: unknown) => v === null || typeof v === 'string'
export function sellerLabel(status: string) {
  switch (status) { case 'pending_payment': return 'Registration payment pending'; case 'pending_approval': return 'Awaiting approval'; case 'active': return 'Active'; case 'suspended': return 'Suspended'; case 'rejected': return 'Rejected'; default: return 'Status unavailable' }
}
export function sellerMoney(value: string) {
  if (!money(value)) return fail()
  const units = paisa(value)
  return `PKR ${(units / 100n).toLocaleString('en-PK')}.${String(units % 100n).padStart(2, '0')}`
}
export function validateAdminSeller(row: AdminSeller) {
  if (!row || !text(row.id) || !isOrderId(row.id) || !text(row.brand_name) || !text(row.status)
    || ![row.slots_used, row.total_slots, row.product_count].every(count) || row.slots_used > row.total_slots
    || ![row.total_gmv, row.platform_cut, row.available_balance].every(money)
    || !text(row.joined_at) || !/^\d{4}-\d{2}-\d{2}T/.test(row.joined_at) || !Number.isFinite(Date.parse(row.joined_at))) return fail()
  return row
}
export function validateAdminSellers(value: AdminSellerPage, page: number, status: string) {
  if (!value || !Array.isArray(value.data) || !count(value.total) || value.page !== page || value.per_page !== 25
    || value.total_pages !== Math.max(1, Math.ceil(value.total / 25)) || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateAdminSeller(row); if (ids.has(row.id) || (status !== 'all' && row.status !== status)) return fail(); ids.add(row.id) }
  return value
}
export function validateAdminSellerDetail(value: AdminSellerDetail, id: string) {
  validateAdminSeller(value)
  if (value.id !== id || !text(value.slug) || ![value.description, value.whatsapp_number, value.instagram_handle, value.logo_url, value.return_policy, value.rejected_reason].every(nullableText)
    || !money(value.pending_balance) || !money(value.registration_fee)) return fail()
  if (!money(value.registration_amount_due) || !nullableText(value.registration_payment_reference)
    || !(value.registration_paid_by === null || (text(value.registration_paid_by) && isOrderId(value.registration_paid_by)))
    || !(value.registration_paid_at === null || (text(value.registration_paid_at) && /^\d{4}-\d{2}-\d{2}T/.test(value.registration_paid_at) && Number.isFinite(Date.parse(value.registration_paid_at))))
    || paisa(value.registration_amount_due) !== (value.status === 'pending_payment' && value.registration_paid_at === null ? paisa(value.registration_fee) : 0n)) return fail()
  return value
}
export function sellerDecisions(status: string): SellerDecision[] {
  switch (status) { case 'pending_approval': return ['approve', 'reject']; case 'pending_payment': return ['reject']; case 'active': return ['suspend']; case 'suspended': return ['reinstate']; default: return [] }
}
export function sellerDecisionBody(status: string, action: SellerDecision, reason: string): { reason?: string } {
  if (!sellerDecisions(status).includes(action)) throw new Error('This decision is not available for the current seller status.')
  if (action !== 'reject' && action !== 'suspend') return {}
  const value = reason.trim()
  if (value.length < 10 || value.length > 1000 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) throw new Error('Enter a clear reason between 10 and 1,000 characters.')
  return { reason: value }
}
/** Review content must be rechecked, while live wallet/product counts may change. */
export function sameSellerReview(before: AdminSellerDetail, latest: AdminSellerDetail) {
  return (['id', 'status', 'brand_name', 'slug', 'description', 'whatsapp_number', 'instagram_handle', 'logo_url', 'return_policy', 'registration_fee', 'rejected_reason', 'registration_amount_due', 'registration_paid_at', 'registration_payment_reference', 'registration_paid_by'] as const).every((key) => before[key] === latest[key])
}
export interface RegistrationPayment { amount: string; reference: string }
export function canRecordRegistration(value: AdminSellerDetail) {
  return value.status === 'pending_payment' && value.registration_paid_at === null && value.registration_payment_reference === null && value.registration_paid_by === null && paisa(value.registration_amount_due) > 0n
}
export function registrationPaymentBody(value: AdminSellerDetail, amount: string, reference: string): RegistrationPayment {
  validateAdminSellerDetail(value, value.id)
  if (!canRecordRegistration(value)) throw new Error('This seller is not eligible for a new registration payment record.')
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(amount) || paisa(amount) !== paisa(value.registration_amount_due)) throw new Error('Enter the exact outstanding registration amount, with up to two decimal places.')
  const ref = reference.trim()
  if (ref.length < 3 || ref.length > 255 || /[\x00-\x1f\x7f]/.test(ref)) throw new Error('Enter a transfer reference of 3–255 characters without control characters.')
  const units = paisa(amount)
  return { amount: `${units / 100n}.${String(units % 100n).padStart(2, '0')}`, reference: ref }
}
export function confirmRegistrationPayment(value: AdminSellerDetail, before: AdminSellerDetail, body: RegistrationPayment, owner: string) {
  registrationPaymentBody(before, body.amount, body.reference)
  validateAdminSellerDetail(value, before.id)
  if (!value.registration_paid_at || value.registration_payment_reference !== body.reference || value.registration_paid_by !== owner
    || paisa(value.registration_fee) !== paisa(body.amount) || paisa(value.registration_amount_due) !== 0n || !['pending_approval', 'active', 'suspended', 'rejected'].includes(value.status)) return fail()
  return value
}
export function confirmSellerDecision(value: AdminSellerDetail, before: AdminSellerDetail, action: SellerDecision, body: { reason?: string }) {
  validateAdminSellerDetail(value, before.id)
  sellerDecisionBody(before.status, action, body.reason ?? '')
  const status = action === 'approve' || action === 'reinstate' ? 'active' : action === 'reject' ? 'rejected' : 'suspended'
  if (value.status !== status || (body.reason !== undefined && value.rejected_reason !== body.reason)) return fail()
  return value
}
export const sellerDecisionMarker = (owner: string, id: string) => `wearhowz:admin-seller-pending:${owner}:${id}`
export function sellerLogo(value: string | null) {
  try { const url = new URL(value ?? ''); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null } catch { return null }
}
