import { expect, it } from 'vitest'
import { refundConfirmPayload, refundMarker, refundQuery, refundReceipt, refundRequestPayload, validateRefundDetail, validateRefundHistory, validateRefunds, type RefundDetail, type RefundHistory, type RefundRow } from './refunds'
const id = '11111111-1111-4111-8111-111111111111', payment = '22222222-2222-4222-8222-222222222222', owner = '33333333-3333-4333-8333-333333333333'
const row = (): RefundRow => ({ refund_id: id, payment_id: payment, order_id: payment, order_number: 'WHZ-001', return_id: null, status: 'pending', amount: '500.25', currency: 'PKR', reason: 'Customer refund', transfer_reference: null, requested_by: owner, confirmed_by: null, requested_at: '2026-11-04T00:00:00Z', processed_at: null, accounting: null })
const history = (): RefundHistory => ({ payment_id: payment, order_id: payment, order_number: 'WHZ-001', payment_status: 'completed', payment_method: 'cod', payment_amount: '2600.00', currency: 'PKR', pending_refund_amount: '500.25', completed_refund_amount: '0', reserved_refund_amount: '500.25', remaining_refundable_amount: '2099.75', can_request_refund: true, refunds: [row()] })
const detail = (): RefundDetail => ({ ...row(), payment: history(), history: [{ event: 'requested', occurred_at: row().requested_at, actor_id: owner, transfer_reference: null }], can_confirm_refund: true, confirmation_blockers: [], linked_return_status: null })
it('builds supported filters and validates paginated refund identities', () => {
  expect(refundQuery('all', '', '2')).toBe('page=2')
  expect(refundQuery('pending', payment, '1')).toContain(`payment_id=${payment}`)
  for (const args of [['unknown', '', '1'], ['all', 'bad', '1'], ['all', '', '0']]) expect(() => refundQuery(...args as [string, string, string])).toThrow()
  const value = { data: [row()], total: 1, page: 1, per_page: 25, total_pages: 1 }
  expect(validateRefunds(value, 1, 'pending', payment)).toBe(value)
  for (const bad of [{ ...value, total_pages: 2 }, { ...value, data: [row(), row()] }, { ...value, data: [{ ...row(), amount: 500.25 }] }]) expect(() => validateRefunds(bad as typeof value, 1, 'pending', payment)).toThrow()
})
it('verifies remaining balance, pending/completed totals and whole history', () => {
  expect(validateRefundHistory(history(), payment).remaining_refundable_amount).toBe('2099.75')
  for (const fields of [{ remaining_refundable_amount: '2100' }, { refunds: [] }, { refunds: [row(), row()] }, { reserved_refund_amount: '500' }, { currency: 'USD' }, { refunds: [{ ...row(), payment_id: owner }] }]) expect(() => validateRefundHistory({ ...history(), ...fields }, payment)).toThrow()
})
it('checks detail identity, history actors and confirmation eligibility', () => {
  expect(validateRefundDetail(detail(), id).can_confirm_refund).toBe(true)
  for (const fields of [{ refund_id: owner }, { history: [] }, { can_confirm_refund: false }, { confirmation_blockers: ['Blocked'] }, { transfer_reference: 'UNEXPECTED' }, { return_id: owner, linked_return_status: 'approved' }]) expect(() => validateRefundDetail({ ...detail(), ...fields } as RefundDetail, id)).toThrow()
})
it('requires exact positive request amounts, meaningful reasons and explicit review', () => {
  expect(refundRequestPayload(history(), '100.25', '  Customer refund  ', true, owner)).toEqual({ amount: '100.25', reason: 'Customer refund', idempotency_key: owner, expected_remaining_amount: '2099.75' })
  for (const amount of ['0', '-1', '2100', '1.001', '1e2', '']) expect(() => refundRequestPayload(history(), amount, 'Customer refund', true, owner)).toThrow()
  expect(() => refundRequestPayload(history(), '100', 'Customer refund', false, owner)).toThrow()
  expect(() => refundRequestPayload(history(), '100', 'bad', true, owner)).toThrow()
})
it('requires an actual transfer reference and sends explicit nullable return expectations', () => {
  expect(refundConfirmPayload(detail(), '  BANK-001  ', true)).toEqual({ reference: 'BANK-001', expected_amount: '500.25', expected_payment_id: payment, expected_return_id: null })
  for (const reference of ['', 'ab', 'ab\nc', 'x'.repeat(256)]) expect(() => refundConfirmPayload(detail(), reference, true)).toThrow()
  expect(() => refundConfirmPayload(detail(), 'BANK-001', false)).toThrow()
})
it('rejects ambiguous or mismatched structured receipts and isolates operation markers', () => {
  const receipt = { refund_id: id, payment_id: payment, amount: '500.25', reason: 'Customer refund', gateway_ref: null, created_at: row().requested_at, status: 'pending', processed_at: null }
  expect(refundReceipt(receipt, payment, '500.25', 'Customer refund', 'pending')).toBe(receipt)
  expect(() => refundReceipt({ ...receipt, amount: '500.24' }, payment, '500.25', 'Customer refund', 'pending')).toThrow()
  expect(() => refundReceipt({ ...receipt, status: 'completed' }, payment, '500.25', 'Customer refund', 'pending')).toThrow()
  expect(refundMarker(owner, 'request', payment)).not.toBe(refundMarker(owner, 'confirm', payment))
  expect(refundMarker(owner, 'request', payment)).not.toBe(refundMarker(id, 'request', payment))
})
it('verifies allocation totals without hiding platform shortfalls or settlement offsets', () => {
  const allocation = { seller_order_id: owner, seller_id: owner, merchandise_amount: '500.25', commission_rate: '0.15', commission_reversal_amount: '75.04', seller_reversal_amount: '425.21', recovered_amount: '400', settlement_offset_amount: '0', platform_shortfall_amount: '25.21', reconciled: true }
  const accounting = { ...allocation, shipping_amount: '0', platform_funded_amount: '100.25', allocations: [allocation] }
  const completed = { ...detail(), payment: { ...history(), pending_refund_amount: '0', completed_refund_amount: '500.25' }, status: 'completed' as const, processed_at: '2026-11-04T01:00:00Z', transfer_reference: 'BANK-001', confirmed_by: owner, accounting, can_confirm_refund: false, confirmation_blockers: ['Already recorded'], history: [...detail().history, { event: 'completed' as const, occurred_at: '2026-11-04T01:00:00Z', actor_id: owner, transfer_reference: 'BANK-001' }] }
  expect(validateRefundDetail(completed, id).accounting?.platform_shortfall_amount).toBe('25.21')
  expect(() => validateRefundDetail({ ...completed, accounting: { ...accounting, recovered_amount: '399' } }, id)).toThrow()
})
