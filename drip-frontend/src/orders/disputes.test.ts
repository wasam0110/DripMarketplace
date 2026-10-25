import { expect, it } from 'vitest'
import { ApiError } from '../api/client'
import { canMessage, disputeStatus, disputeText, missingDispute, validateDispute, validateMessage } from './disputes'
const id = '11111111-1111-4111-8111-111111111111'
const other = '22222222-2222-4222-8222-222222222222'
const message = { id, sender_id: id, body: 'Please review this return.', created_at: '2026-10-23T10:00:00Z' }
const detail = { id, return_id: id, seller_id: id, status: 'open', created_at: message.created_at, resolved_at: null, resolution_note: null, messages: [message] }
it('validates dispute and message references, dates and unique messages', () => {
  expect(validateDispute(detail, id)).toBe(detail)
  expect(validateMessage(message)).toBe(message)
  expect(() => validateDispute(detail, other)).toThrow()
  expect(() => validateDispute({ ...detail, messages: [message, message] }, id)).toThrow()
  expect(() => validateMessage({ ...message, created_at: 'invalid' })).toThrow()
  expect(() => validateMessage({ ...message, body: '' })).toThrow()
})
it('uses the separate trimmed text limits for opening and replies', () => {
  expect(disputeText('  Please review this.  ', true)).toBe('Please review this.')
  expect(disputeText(' x ', false)).toBe('x')
  expect(() => disputeText('short', true)).toThrow()
  expect(() => disputeText('   ', false)).toThrow()
  expect(() => disputeText('x'.repeat(2001), false)).toThrow()
})
it('only treats the explicit missing-dispute sentinel as absence', () => {
  expect(missingDispute(new ApiError('No dispute found for this return not found.', 404, 'NOT_FOUND'))).toBe(true)
  expect(missingDispute(new ApiError('Return not found.', 404, 'NOT_FOUND'))).toBe(false)
  expect(missingDispute(new ApiError('No dispute found for this return not found.', 403, 'NOT_FOUND'))).toBe(false)
})
it('allows messages only in known active states', () => {
  expect(canMessage('open')).toBe(true); expect(canMessage('under_review')).toBe(true)
  for (const status of ['resolved_customer', 'resolved_seller', 'closed', 'unknown']) expect(canMessage(status)).toBe(false)
  expect(disputeStatus('__proto__')).toBe('Status unavailable')
})
