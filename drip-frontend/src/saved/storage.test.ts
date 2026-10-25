import { expect, it, vi } from 'vitest'
import { changeSaved, MAX_SAVED, parseSaved, readSaved, SAVED_KEY, writeSaved } from './storage'

const a = '11111111-1111-4111-8111-111111111111'
const b = '22222222-2222-4222-8222-222222222222'
it('persists only product identifiers and supports removal', () => {
  expect(parseSaved(null)).toEqual([])
  writeSaved([a, b])
  expect(readSaved()).toEqual([a, b])
  expect(localStorage.getItem(SAVED_KEY)).toBe(JSON.stringify([a, b]))
  writeSaved([])
  expect(localStorage.getItem(SAVED_KEY)).toBeNull()
})
it.each(['broken', '{}', '[null]', '["invalid"]', JSON.stringify([a, a])])('rejects malformed saved data without overwriting it: %s', (raw) => {
  localStorage.setItem(SAVED_KEY, raw)
  expect(() => readSaved()).toThrow()
  expect(localStorage.getItem(SAVED_KEY)).toBe(raw)
})
it('preserves unrelated current selections and prevents duplicates', () => {
  expect(changeSaved([a, b], a, true)).toEqual([a, b])
  expect(changeSaved([a, b], a, false)).toEqual([b])
  expect(() => changeSaved([], 'invalid', true)).toThrow()
})
it('bounds the list and still allows removal when full', () => {
  const ids = Array.from({ length: MAX_SAVED }, (_, index) => `00000000-0000-4000-8000-${index.toString().padStart(12, '0')}`)
  expect(() => changeSaved(ids, a, true)).toThrow('100')
  expect(changeSaved(ids, ids[0], false)).toHaveLength(MAX_SAVED - 1)
  expect(() => parseSaved(JSON.stringify([...ids, a]))).toThrow()
})
it('does not mask storage permission errors as a successful save', () => {
  const storage = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
  expect(() => writeSaved([a])).toThrow('Storage blocked')
  storage.mockRestore()
})
