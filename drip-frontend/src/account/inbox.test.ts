import { describe, expect, it } from 'vitest'
import { notificationLink, validateInbox } from './inbox'
const row = { id: '11111111-1111-4111-8111-111111111111', type: 'order', title: 'Order update', body: '<b>Plain text</b>', is_read: false, action_url: null, created_at: '2026-10-23T01:00:00Z' }
const inbox = { data: [row], page: 1, total: 1, unread_count: 1 }
describe('notification inbox contracts', () => {
  it('accepts the server snapshot and plain text content', () => expect(validateInbox(inbox, 1)).toEqual(inbox))
  it('rejects a different page', () => expect(() => validateInbox(inbox, 2)).toThrow())
  it('rejects negative counts', () => expect(() => validateInbox({ ...inbox, unread_count: -1 }, 1)).toThrow())
  it('rejects invalid rows', () => expect(() => validateInbox({ ...inbox, data: [{ ...row, is_read: 'false' as never }] }, 1)).toThrow())
  it('rejects duplicated identifiers', () => expect(() => validateInbox({ ...inbox, total: 2, data: [row, row] }, 1)).toThrow())
  it('allows existing order links', () => expect(notificationLink(`/orders/${row.id}`)).toBe(`/orders/${row.id}`))
  it.each(['https://example.test', '//example.test', 'javascript:alert(1)', '/api/v1/me', '/orders/../account', '/orders?token=secret', '/seller/wallet/payouts', '/orders/%2Fexample'])('disables unsupported link %s', (url) => expect(notificationLink(url)).toBeNull())
})
