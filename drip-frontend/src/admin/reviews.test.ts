import { expect, it } from 'vitest'
import { confirmReview, reviewMarker, reviewPayload, reviewQuery, sameReview, validateAdminReview, validateAdminReviews, type AdminReview } from './reviews'
const id = '11111111-1111-4111-8111-111111111111', product = '22222222-2222-4222-8222-222222222222'
export const fixture: AdminReview = { id, product_id: product, user: { id: product, first_name: 'Ayesha', last_name: null, avatar_url: null }, rating: 4, title: 'Great linen', body: '<script>not executable</script>', status: 'pending', is_verified_purchase: true, helpful_count: 0, unhelpful_count: 0, images: [], admin_note: null, moderated_at: null, created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' }
it('supports only real status and pagination filters', () => {
  expect(reviewQuery('pending', '2')).toBe('page=2&status=pending'); expect(reviewQuery('all', '1')).toBe('page=1')
  for (const [status, page] of [['future', '1'], ['all', '0'], ['all', '1.5'], ['all', '999999999999999999']]) expect(() => reviewQuery(status, page)).toThrow()
})
it('validates private fields, identity, ratings and explicit timestamps', () => {
  expect(validateAdminReview(fixture, id)).toBe(fixture)
  for (const changes of [{ id: product }, { admin_note: undefined }, { moderated_at: undefined }, { rating: 0 }, { status: 'future' }, { updated_at: '2026-10-28T00:00:00' }, { user: { ...fixture.user, id: 'bad' } }]) expect(() => validateAdminReview({ ...fixture, ...changes } as AdminReview, id)).toThrow()
})
it('rejects duplicate rows, wrong statuses and malformed pagination', () => {
  const page = { data: [fixture], page: 1, per_page: 25, total: 1 }
  expect(validateAdminReviews(page, 1, 'pending')).toBe(page)
  expect(() => validateAdminReviews(page, 1, 'approved')).toThrow()
  expect(() => validateAdminReviews({ ...page, data: [fixture, fixture], total: 2 }, 1, 'all')).toThrow()
  expect(() => validateAdminReviews(page, 2, 'all')).toThrow()
})
it('trims notes, sends the reviewed version and disallows no-op or unsupported decisions', () => {
  expect(reviewPayload('approved', '  Checked  ', fixture)).toEqual({ status: 'approved', admin_note: 'Checked', expected_updated_at: fixture.updated_at })
  expect(reviewPayload('hidden', ' ', fixture).admin_note).toBeNull()
  expect(() => reviewPayload('pending', '', fixture)).toThrow(); expect(() => reviewPayload('hidden', 'x'.repeat(1001), fixture)).toThrow()
  expect(() => reviewPayload('approved', '', { ...fixture, status: 'approved' })).toThrow()
})
it('rechecks reviewed content but not vote counters', () => {
  expect(sameReview(fixture, { ...fixture, helpful_count: 10 })).toBe(true)
  for (const changes of [{ body: 'Changed' }, { rating: 5 }, { status: 'hidden' as const }, { admin_note: 'Changed' }, { updated_at: '2026-10-28T01:00:00Z' }]) expect(sameReview(fixture, { ...fixture, ...changes })).toBe(false)
})
it('requires a matching saved decision/note and a new server version', () => {
  const payload = reviewPayload('approved', 'Checked', fixture), saved = { ...fixture, ...payload, moderated_at: '2026-10-28T01:00:00Z', updated_at: '2026-10-28T01:00:00Z' }
  expect(confirmReview(saved, fixture, payload)).toBe(saved)
  for (const changes of [{ id: product }, { product_id: id }, { admin_note: null }, { moderated_at: null }, { updated_at: fixture.updated_at }]) expect(() => confirmReview({ ...saved, ...changes }, fixture, payload)).toThrow()
  expect(reviewMarker('a', id)).not.toBe(reviewMarker('b', id))
})
