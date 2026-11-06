import { expect, it } from 'vitest'
import { movedImageIds, validateProductFile, validateProductImages } from './product-media'
const a = { id: '11111111-1111-4111-8111-111111111111', url: 'https://images.example.test/a.webp', alt_text: null, sort_order: 2, is_primary: true }
const b = { ...a, id: '22222222-2222-4222-8222-222222222222', sort_order: 0, is_primary: false }
it('sorts saved images without mutating the response', () => {
  const original = [a, b]; expect(validateProductImages(original)).toEqual([b, a]); expect(original).toEqual([a, b])
})
it('reorders complete IDs and rejects boundary moves', () => {
  expect(movedImageIds([a, b], a.id, 1)).toEqual([b.id, a.id])
  expect(() => movedImageIds([a, b], a.id, -1)).toThrow()
})
it.each(['javascript:alert(1)', 'http://images.example.test/a', 'https://user:pass@example.test/a'])('rejects unsafe URL %s', (url) => {
  expect(() => validateProductImages([{ ...a, url }])).toThrow()
})
it('rejects duplicates and multiple primary images', () => {
  expect(() => validateProductImages([a, a])).toThrow()
  expect(() => validateProductImages([a, { ...b, is_primary: true }])).toThrow()
})
it.each([{ size: 0, type: 'image/png' }, { size: 5 * 1024 * 1024 + 1, type: 'image/png' }, { size: 1, type: 'image/svg+xml' }])('rejects invalid file %j', (file) => {
  expect(() => validateProductFile(file)).toThrow()
})
it('accepts the product-specific five MiB limit', () => {
  expect(() => validateProductFile({ size: 5 * 1024 * 1024, type: 'image/webp' })).not.toThrow()
})
