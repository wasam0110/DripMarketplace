import { expect, it } from 'vitest'
import { canRecordRegistration, confirmRegistrationPayment, registrationPaymentBody } from './sellers'
import { confirmSellerDecision, sameSellerReview, sellerDecisionBody, sellerDecisionMarker, sellerDecisions, sellerLogo, sellerMoney, validateAdminSellerDetail, validateAdminSellers, type AdminSellerDetail } from './sellers'
const id = '11111111-1111-4111-8111-111111111111'
const detail: AdminSellerDetail = { id, brand_name: 'Test Label', status: 'pending_approval', slots_used: 1, total_slots: 5, product_count: 1, total_gmv: '1000.25', platform_cut: '150.03', available_balance: '500.25', joined_at: '2026-10-28T10:00:00Z', slug: 'test-label', description: 'Independent label', whatsapp_number: null, instagram_handle: null, logo_url: null, return_policy: 'Seven-day returns', pending_balance: '200', registration_fee: '0', rejected_reason: null, registration_amount_due: '0', registration_paid_at: null, registration_payment_reference: null, registration_paid_by: null }
it.each([
  ['pending_approval', ['approve', 'reject']], ['pending_payment', ['reject']], ['active', ['suspend']], ['suspended', ['reinstate']], ['rejected', []], ['future', []], ['constructor', []],
])('exposes only server-supported decisions for %s', (status, actions) => expect(sellerDecisions(status as string)).toEqual(actions))
it('validates an owning seller detail and rejects missing financial/context fields', () => {
  expect(validateAdminSellerDetail(detail, id)).toBe(detail)
  expect(() => validateAdminSellerDetail(detail, '22222222-2222-4222-8222-222222222222')).toThrow()
  expect(() => validateAdminSellerDetail({ ...detail, pending_balance: undefined! }, id)).toThrow()
  expect(() => validateAdminSellerDetail({ ...detail, slots_used: 6 }, id)).toThrow()
  expect(() => validateAdminSellerDetail({ ...detail, description: undefined! }, id)).toThrow()
})
it('validates requested pagination and status without treating an unknown state as permission', () => {
  const page = { data: [detail], total: 26, page: 1, per_page: 25, total_pages: 2 }
  expect(validateAdminSellers(page, 1, 'pending_approval')).toBe(page)
  expect(() => validateAdminSellers(page, 2, 'pending_approval')).toThrow()
  expect(() => validateAdminSellers(page, 1, 'active')).toThrow()
  expect(() => validateAdminSellers({ ...page, data: [detail, detail] }, 1, 'all')).toThrow()
  expect(() => validateAdminSellers({ ...page, total_pages: 1 }, 1, 'all')).toThrow()
})
it('requires trimmed rejection/suspension reasons and omits reasons for approval', () => {
  expect(sellerDecisionBody('pending_approval', 'reject', '  Please provide brand details.  ')).toEqual({ reason: 'Please provide brand details.' })
  expect(sellerDecisionBody('active', 'suspend', 'Policy violation confirmed.')).toEqual({ reason: 'Policy violation confirmed.' })
  expect(sellerDecisionBody('pending_approval', 'approve', 'Unused reason')).toEqual({})
  expect(() => sellerDecisionBody('pending_approval', 'reject', '     short     ')).toThrow()
  expect(() => sellerDecisionBody('active', 'suspend', 'x'.repeat(1001))).toThrow()
  expect(() => sellerDecisionBody('pending_payment', 'approve', '')).toThrow()
})
it('preflight detects changes to reviewed application content, not volatile balances', () => {
  expect(sameSellerReview(detail, { ...detail, available_balance: '0', product_count: 2 })).toBe(true)
  expect(sameSellerReview(detail, { ...detail, status: 'rejected' })).toBe(false)
  expect(sameSellerReview(detail, { ...detail, return_policy: 'No returns' })).toBe(false)
  expect(sameSellerReview(detail, { ...detail, registration_fee: '5000' })).toBe(false)
})
it.each(['approve', 'reject', 'suspend', 'reinstate'] as const)('confirms exact server state after %s', (action) => {
  const before = { ...detail, status: action === 'suspend' ? 'active' : action === 'reinstate' ? 'suspended' : 'pending_approval' }
  const body = sellerDecisionBody(before.status, action, 'Please provide brand details.')
  const saved = { ...detail, status: action === 'reject' ? 'rejected' : action === 'suspend' ? 'suspended' : 'active', rejected_reason: body.reason ?? null }
  expect(confirmSellerDecision(saved, before, action, body)).toBe(saved)
  expect(() => confirmSellerDecision({ ...saved, status: 'future' }, before, action, body)).toThrow()
  if (body.reason) expect(() => confirmSellerDecision({ ...saved, rejected_reason: 'Another reason' }, before, action, body)).toThrow()
})
it('formats exact aggregate money and permits only credential-free HTTPS logos', () => {
  expect(sellerMoney('9007199254740993.25')).toBe('PKR 9,007,199,254,740,993.25')
  expect(() => sellerMoney('1e3')).toThrow()
  for (const url of [null, 'javascript:alert(1)', 'data:image/png;base64,abc', 'http://example.test/a', 'https://user:pass@example.test/a']) expect(sellerLogo(url)).toBeNull()
  expect(sellerLogo('https://example.test/logo.png')).toBe('https://example.test/logo.png')
  expect(sellerDecisionMarker('owner-a', id)).not.toBe(sellerDecisionMarker('owner-b', id))
})

const unpaid = { ...detail, status: 'pending_payment', registration_fee: '5000.25', registration_amount_due: '5000.25' }
it('creates an exact reviewed registration record without a number conversion', () => {
  expect(registrationPaymentBody(unpaid, '05000.25', '  BANK-123  ')).toEqual({ amount: '5000.25', reference: 'BANK-123' })
  expect(canRecordRegistration(unpaid)).toBe(true)
  for (const amount of ['5000.24', '5000.26', '5000.251', '5e3', '0', '-1']) expect(() => registrationPaymentBody(unpaid, amount, 'BANK-123')).toThrow()
})
it('does not invent zero-fee receipts or overwrite partial historical metadata', () => {
  expect(canRecordRegistration(detail)).toBe(false)
  expect(canRecordRegistration({ ...unpaid, registration_payment_reference: 'LEGACY' })).toBe(false)
  expect(() => registrationPaymentBody(detail, '0', 'BANK-123')).toThrow()
  expect(() => registrationPaymentBody(unpaid, '5000.25', '   ')).toThrow()
  expect(() => registrationPaymentBody(unpaid, '5000.25', 'bank\nreference')).toThrow()
  expect(() => validateAdminSellerDetail({ ...unpaid, registration_amount_due: '0' }, id)).toThrow()
  expect(() => validateAdminSellerDetail({ ...detail, registration_paid_at: undefined! }, id)).toThrow()
})
it('requires the exact reference, amount, recording actor and saved receipt before confirmation', () => {
  const body = registrationPaymentBody(unpaid, '5000.25', 'BANK-123')
  const saved = { ...unpaid, status: 'pending_approval', registration_amount_due: '0', registration_paid_at: '2026-10-28T12:00:00Z', registration_payment_reference: 'BANK-123', registration_paid_by: id }
  expect(confirmRegistrationPayment(saved, unpaid, body, id)).toBe(saved)
  expect(confirmRegistrationPayment({ ...saved, status: 'active' }, unpaid, body, id).status).toBe('active')
  for (const changed of [{ registration_paid_by: '22222222-2222-4222-8222-222222222222' }, { registration_payment_reference: 'OTHER' }, { registration_fee: '5000.26' }, { registration_paid_at: null }, { registration_amount_due: '1' }]) expect(() => confirmRegistrationPayment({ ...saved, ...changed }, unpaid, body, id)).toThrow()
  expect(sameSellerReview(unpaid, { ...unpaid, registration_paid_by: id })).toBe(false)
})
