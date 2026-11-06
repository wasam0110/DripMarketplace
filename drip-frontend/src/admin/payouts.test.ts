import { expect, it } from 'vitest'
import { confirmPayout, payoutActions, payoutBody, payoutMarker, validateAdminPayout, validatePayoutList, type AdminPayout } from './payouts'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222'
const row = (): AdminPayout => ({ id, seller_id: seller, amount: '500.25', payment_method: 'bank_transfer', payment_detail: 'Synthetic Bank — 000001', status: 'requested', admin_note: null, requested_at: '2026-11-05T00:00:00Z', completed_at: null, transfer_reference: null, last_action_by: null, available_actions: ['approve', 'reject'] })
it('checks payout identity and limits actions to the saved state', () => {
  expect(validateAdminPayout(row(), id)).toEqual(row())
  for (const fields of [{ id: seller }, { seller_id: 'bad' }, { status: 'unknown' }, { available_actions: ['complete'] }, { last_action_by: 'bad' }, { transfer_reference: 'existing' }]) expect(() => validateAdminPayout({ ...row(), ...fields }, id)).toThrow()
  expect(payoutActions({ ...row(), status: 'processing', available_actions: ['complete'] })).toEqual(['complete'])
  expect(payoutActions({ ...row(), status: 'rejected', available_actions: [] })).toEqual([])
})
it('checks completion evidence and list status/pagination', () => {
  expect(() => validateAdminPayout({ ...row(), status: 'completed', available_actions: [] }, id)).toThrow()
  const page = { data: [row()], page: 1, total: 1, total_pages: 1 }
  expect(validatePayoutList(page, 1, 'requested')).toBe(page)
  expect(() => validatePayoutList(page, 1, 'approved')).toThrow()
  expect(() => validatePayoutList({ ...page, data: [row(), row()] }, 1, 'requested')).toThrow()
})
it('requires explicit review and includes the exact saved snapshot', () => {
  const body = payoutBody(row(), 'approve', '  Checked  ', '', true)
  expect(body.admin_note).toBe('Checked')
  expect(body.review).toEqual({ expected_status: 'requested', expected_amount: '500.25', expected_seller_id: seller, expected_payment_method: 'bank_transfer', expected_payment_detail: row().payment_detail, expected_admin_note: null })
  expect(() => payoutBody(row(), 'approve', '', '', false)).toThrow()
  expect(() => payoutBody(row(), 'complete', '', 'BANK-001', true)).toThrow()
  for (const note of ['', '  ', 'x'.repeat(501), 'bad\u0000note']) expect(() => payoutBody(row(), 'reject', note, '', true)).toThrow()
})
it('requires a real reference and validates successful receipts field by field', () => {
  const before = { ...row(), status: 'approved', available_actions: ['complete'] }
  for (const ref of ['', 'ab', 'a\nb', 'x'.repeat(256)]) expect(() => payoutBody(before, 'complete', '', ref, true)).toThrow()
  const body = payoutBody(before, 'complete', '', ' BANK-001 ', true)
  const receipt = { ...before, status: 'completed', transfer_reference: 'BANK-001', completed_at: '2026-11-05T01:00:00Z' }
  expect(confirmPayout(receipt, before, 'complete', body)).toBe(receipt)
  for (const fields of [{ amount: '500.26' }, { payment_detail: 'Other bank' }, { transfer_reference: 'OTHER' }, { completed_at: null }, { admin_note: 'Unexpected' }, { id: seller }]) expect(() => confirmPayout({ ...receipt, ...fields }, before, 'complete', body)).toThrow()
})
it('preserves omitted notes and isolates uncertainty by owner and payout', () => {
  const before = { ...row(), admin_note: 'Saved note' }, body = payoutBody(before, 'approve', '', '', true)
  expect(confirmPayout({ ...before, status: 'approved' }, before, 'approve', body).admin_note).toBe('Saved note')
  expect(payoutMarker(id, seller)).not.toBe(payoutMarker(seller, seller))
  expect(payoutMarker(id, seller)).not.toBe(payoutMarker(id, id))
})
