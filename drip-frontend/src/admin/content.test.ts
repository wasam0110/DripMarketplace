import { expect, it } from 'vitest'
import { bannerDraft, bannerLink, bannerMarker, bannerPayload, confirmBanner, sameBanner, validateBanner, validateBannerFile, validateBanners, type AdminBanner } from './content'
const row: AdminBanner = { id: '11111111-1111-4111-8111-111111111111', title: 'Linen season', image_url: 'https://example.test/banner.webp', link_url: '/clothing', position: 'homepage_hero', sort_order: 0, is_active: false, valid_from: null, valid_until: null, created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' }
it('requires complete identifiable banner records and unique list identities', () => {
  expect(validateBanner(row)).toBe(row); expect(validateBanners([])).toEqual([])
  for (const changes of [{ id: 'bad' }, { updated_at: undefined }, { position: 'unknown' }, { sort_order: -1 }, { is_active: undefined }, { valid_from: 'invalid' }]) expect(() => validateBanner({ ...row, ...changes } as AdminBanner)).toThrow()
  expect(() => validateBanners([row, row])).toThrow()
})
it('accepts only safe local/HTTPS destinations and supports clearing', () => {
  expect(bannerLink(' /clothing?q=linen ')).toBe('/clothing?q=linen'); expect(bannerLink(' ')).toBeNull(); expect(bannerLink('https://example.test/a')).toBe('https://example.test/a')
  for (const value of ['javascript:alert(1)', 'http://example.test', '//example.test', '/\\example.test', 'https://user:pass@example.test', 'https://', 'https://example.test:99999', '/a\nb']) expect(() => bannerLink(value)).toThrow()
})
it('defaults new banners to inactive without inventing initial scheduling support', () => {
  const draft = { ...bannerDraft(), title: '  New banner  ', start: '2026-10-29T10:00' }
  expect(bannerPayload(draft)).toEqual({ title: 'New banner', link_url: null, position: 'homepage_hero', sort_order: 0, is_active: false, valid_from: null, valid_until: null })
})
it('validates numeric order, title, link limits and rejects no-op edits', () => {
  expect(() => bannerPayload(bannerDraft(row), row)).toThrow('Change a banner field')
  for (const changes of [{ title: ' ' }, { order: '-1' }, { order: '1.5' }, { order: '2147483648' }, { link: 'x'.repeat(501) }]) expect(() => bannerPayload({ ...bannerDraft(row), ...changes }, row)).toThrow()
})
it('keeps unchanged second precision while changing and clearing UTC schedule limits', () => {
  const initial = { ...row, valid_from: '2026-10-29T10:00:45+05:00', valid_until: '2026-10-30T05:00:00Z' }
  const draft = { ...bannerDraft(initial), title: 'New heading' }
  expect(draft.start).toBe('2026-10-29T05:00'); expect(bannerPayload(draft, initial).valid_from).toBe(initial.valid_from)
  expect(bannerPayload({ ...draft, start: '', end: '' }, initial).valid_from).toBeNull()
  expect(() => bannerPayload({ ...draft, start: '2026-11-30T10:00', end: '2026-11-29T10:00' }, initial)).toThrow('end must follow')
  expect(() => bannerPayload({ ...draft, start: '2026-02-30T10:00' }, initial)).toThrow('valid UTC')
})
it('binds confirmation to unchanged image, identity, fields and a new saved version', () => {
  const payload = bannerPayload({ ...bannerDraft(row), title: 'Changed' }, row), saved = { ...row, ...payload, updated_at: '2026-10-28T01:00:00Z' }
  expect(confirmBanner(saved, payload, row)).toBe(saved); expect(sameBanner(row, saved)).toBe(false)
  for (const changes of [{ id: '22222222-2222-4222-8222-222222222222' }, { image_url: 'https://example.test/other.webp' }, { title: 'Wrong' }, { updated_at: row.updated_at }]) expect(() => confirmBanner({ ...saved, ...changes }, payload, row)).toThrow()
})
it('enforces local upload limits and isolates pending markers', () => {
  expect(() => validateBannerFile({ type: 'image/png', size: 5 * 1024 * 1024 })).not.toThrow()
  for (const file of [{ type: 'image/svg+xml', size: 100 }, { type: 'image/png', size: 0 }, { type: 'image/png', size: 5 * 1024 * 1024 + 1 }]) expect(() => validateBannerFile(file)).toThrow()
  expect(bannerMarker('a', 'new')).not.toBe(bannerMarker('b', 'new'))
})
