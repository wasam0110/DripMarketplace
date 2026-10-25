import { expect, it } from 'vitest'
import { returnStatus, validateReturnDetail, validateReturnList, type ReturnDetail } from './returnHistory'
const id = '11111111-1111-4111-8111-111111111111'
const other = '22222222-2222-4222-8222-222222222222'
const detail: ReturnDetail = { id, order_id: id, seller_order_id: id, status: 'requested', reason: 'The fit was not right.', item_count: 1, requested_at: '2026-10-23T10:00:00Z', resolved_at: null, notes: null, items: [{ id, order_item_id: id, quantity: 1, reason: null }] }
it('validates the flat paginated return contract', () => {
  const list = { data: [detail], total: 1, page: 1, total_pages: 1 }
  expect(validateReturnList(list, 1)).toBe(list)
  expect(validateReturnList({ data: [], total: 0, page: 1, total_pages: 1 }, 1).total).toBe(0)
  for (const changes of [{ page: 2 }, { total: -1 }, { total_pages: 2 }, { data: [detail, detail] }]) expect(() => validateReturnList({ ...list, ...changes }, 1)).toThrow()
})
it('rejects mismatched references, malformed dates and duplicate/invalid item rows', () => {
  expect(validateReturnDetail(detail, id)).toBe(detail)
  expect(() => validateReturnDetail(detail, other)).toThrow()
  for (const changes of [{ requested_at: 'invalid' }, { resolved_at: 'invalid' }, { notes: undefined }, { items: [] }, { item_count: 2, items: [detail.items[0], detail.items[0]] }, { items: [{ ...detail.items[0], quantity: 0 }] }]) expect(() => validateReturnDetail({ ...detail, ...changes } as ReturnDetail, id)).toThrow()
})
it('does not invent status or bank confirmations', () => {
  for (const status of ['requested', 'approved', 'rejected', 'received', 'refunded']) expect(returnStatus(status).label).not.toBe('Status unavailable')
  expect(returnStatus('refunded').description).toContain('does not provide')
  expect(returnStatus('future-status').label).toBe('Status unavailable')
  expect(returnStatus('__proto__').label).toBe('Status unavailable')
})
