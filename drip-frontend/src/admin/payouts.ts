import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import { payoutStatuses, validatePayout, validateWalletPage, type Payout, type WalletPage } from '../seller/wallet'
export type PayoutAction = 'approve' | 'reject' | 'complete'
export interface AdminPayout extends Payout { seller_id: string; last_action_by: string | null; available_actions: string[] }
const fail = () => { throw new Error('Payout records could not be verified. Refresh before making changes.') }
export function validateAdminPayout(v: AdminPayout, id: string) {
  validatePayout(v)
  if (v.id !== id || !payoutStatuses.includes(v.status) || !isOrderId(v.seller_id) || (v.last_action_by !== null && !isOrderId(v.last_action_by))
    || !Array.isArray(v.available_actions) || v.available_actions.some(a => !['approve', 'reject', 'complete'].includes(a)) || new Set(v.available_actions).size !== v.available_actions.length) return fail()
  if (v.status === 'completed' && (!v.transfer_reference?.trim() || !v.completed_at)) return fail()
  if (v.available_actions.some(a => !allowed(v).includes(a as PayoutAction))) return fail()
  return v
}
function allowed(v: Payout): PayoutAction[] {
  if (v.transfer_reference !== null || v.completed_at !== null || paisa(v.amount) <= 0n) return []
  return v.status === 'requested' ? ['approve', 'reject'] : v.status === 'approved' ? ['reject', 'complete'] : v.status === 'processing' ? ['complete'] : []
}
export const payoutActions = (v: AdminPayout) => allowed(v).filter(a => v.available_actions.includes(a))
export function validatePayoutList(v: WalletPage<Payout>, page: number, status: string) {
  validateWalletPage(v, page, validatePayout)
  if (v.data.some(row => row.status !== status)) return fail()
  return v
}
export function payoutBody(v: AdminPayout, action: PayoutAction, note: string, reference: string, checked: boolean) {
  if (!payoutActions(v).includes(action) || !checked) throw new Error('Review the payout and acknowledge the selected action.')
  const text = note.trim(), ref = reference.trim()
  if (text.length > 500 || action === 'reject' && !text || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text)) throw new Error('Rejection requires a meaningful note; use up to 500 characters.')
  if (action === 'complete' && (ref.length < 3 || ref.length > 255 || /[\x00-\x1f\x7f]/.test(ref))) throw new Error('Enter the actual transfer reference, 3–255 characters.')
  return { ...(text ? { admin_note: text } : {}), ...(action === 'complete' ? { reference: ref } : {}), review: { expected_status: v.status, expected_amount: v.amount, expected_seller_id: v.seller_id, expected_payment_method: v.payment_method, expected_payment_detail: v.payment_detail, expected_admin_note: v.admin_note } }
}
export function confirmPayout(v: Payout, before: AdminPayout, action: PayoutAction, body: ReturnType<typeof payoutBody>) {
  validatePayout(v)
  const target = { approve: 'approved', reject: 'rejected', complete: 'completed' }[action]
  if (v.id !== before.id || v.status !== target || paisa(v.amount) !== paisa(before.amount) || v.payment_method !== before.payment_method || v.payment_detail !== before.payment_detail || v.requested_at !== before.requested_at || v.admin_note !== (body.admin_note ?? before.admin_note)) return fail()
  if (action === 'complete' ? v.transfer_reference !== body.reference || !v.completed_at : v.transfer_reference !== null || v.completed_at !== null) return fail()
  return v
}
export const payoutActionLabel = (a: PayoutAction) => ({ approve: 'Approve payout', reject: 'Reject payout', complete: 'Record completed transfer' })[a]
export const payoutMarker = (owner: string, id: string) => `wearhowz:admin-payout-pending:${owner}:${id}`
