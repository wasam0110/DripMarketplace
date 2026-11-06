import { expect, it } from 'vitest'
import { returned, disputed, rid, did, other, when } from '../../tests/fixtures/admin-returns'
import { confirmReturn, disputePayload, returnActions, returnPayload, validateAdminDispute, validateAdminReturn, validateDisputes } from './returns'
it('validates admin return identity, quantities and monetary snapshots', () => {
  expect(validateAdminReturn(returned(), rid).id).toBe(rid)
  for (const mutate of [(v: ReturnType<typeof returned>) => { v.order.order_id = did }, (v: ReturnType<typeof returned>) => { v.items[0].line_subtotal = '1.00' }, (v: ReturnType<typeof returned>) => { v.customer = null as never }]) { const v = returned(); mutate(v); expect(() => validateAdminReturn(v, rid)).toThrow() }
})
it('offers only supported actions and requires collected PKR for a new linked refund', () => {
  expect(returnActions(returned())).toEqual(['approve', 'reject'])
  expect(returnActions(returned('received'))).toEqual(['request_refund'])
  for (const currency of ['USD', null]) { const v = returned('received'); v.order.payment_currency = currency; expect(returnActions(v)).toEqual([]) }
  const v = returned('received'); v.order.payment_status = 'pending'; expect(returnActions(v)).toEqual([])
})
it('requires review and includes exact state and estimate expectations', () => {
  expect(() => returnPayload(returned(), 'approve', '', false)).toThrow()
  expect(returnPayload(returned('received'), 'request_refund', '', true)).toEqual({ expected_status: 'received', expected_notes: null, expected_refund_amount: '1080.00' })
  expect(() => returnPayload(returned('received'), 'request_refund', 'x', true)).toThrow()
})
it('verifies saved decision and unchanged item identity', () => {
  const before = returned(), body = returnPayload(before, 'approve', 'Reviewed', true), after = returned('approved'); after.notes = 'Reviewed'
  expect(confirmReturn(after, before, 'approve', body, {})).toBe(after)
  after.notes = 'Another note'; expect(() => confirmReturn(after, before, 'approve', body, {})).toThrow()
})
it('checks linked refund receipt against the saved estimate and id', () => {
  const before = returned('received'), after = returned('received'), body = returnPayload(before, 'request_refund', '', true)
  after.refund = { refund_id: other, status: 'pending', amount: '1080', requested_at: when, processed_at: null, transfer_reference: null }
  expect(confirmReturn(after, before, 'request_refund', body, { refund_id: other, status: 'pending' })).toBe(after)
  expect(() => confirmReturn(after, before, 'request_refund', body, { refund_id: did, status: 'pending' })).toThrow()
})
it('validates dispute identity and rejects duplicate conversation messages', () => {
  const v = disputed(); expect(validateAdminDispute(v, did)).toBe(v)
  expect(() => validateAdminDispute(v, rid)).toThrow(); v.messages.push(v.messages[0]); expect(() => validateAdminDispute(v, did)).toThrow()
})
it('validates dispute pagination and filter membership', () => {
  const v = { data: [disputed()], total: 1, page: 1 }; expect(validateDisputes(v, 1, 'open')).toBe(v)
  expect(() => validateDisputes(v, 2, '')).toThrow(); expect(() => validateDisputes(v, 1, 'closed')).toThrow()
})
it('requires a meaningful reviewed resolution and preserves conversation expectations', () => {
  expect(() => disputePayload(disputed(), 'customer', '   ', true)).toThrow()
  expect(() => disputePayload(disputed(), 'message', 'Hello', false)).toThrow()
  expect(disputePayload(disputed(), 'seller', 'Evidence supports seller', true)).toEqual({ expected_status: 'open', expected_message_count: 1, in_favor_of: 'seller', resolution_note: 'Evidence supports seller' })
  const v = disputed(); v.status = 'closed'; expect(() => disputePayload(v, 'message', 'Hello', true)).toThrow()
})
