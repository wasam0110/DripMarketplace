import { expect, it } from 'vitest'
import { MAX_AVATAR_BYTES, safeAvatarUrl, validateAvatarDimensions, validateAvatarFile, validateAvatarProfile } from './avatar'
it.each(['image/jpeg', 'image/png', 'image/webp'])('accepts %s at the byte limit', (type) => expect(() => validateAvatarFile({ type, size: MAX_AVATAR_BYTES })).not.toThrow())
it.each([0, MAX_AVATAR_BYTES + 1])('rejects invalid byte size %s', (size) => expect(() => validateAvatarFile({ type: 'image/png', size })).toThrow())
it('rejects SVG and unsupported MIME types', () => expect(() => validateAvatarFile({ type: 'image/svg+xml', size: 100 })).toThrow())
it('enforces pixel limits', () => {
  expect(() => validateAvatarDimensions(5000, 5000)).not.toThrow()
  expect(() => validateAvatarDimensions(5001, 5000)).toThrow()
  expect(() => validateAvatarDimensions(0, 100)).toThrow()
})
it.each(['javascript:alert(1)', 'data:image/png;base64,x', '//example.test/a.png', 'http://example.test/a.png', 'https://user:password@example.test/a.png'])('rejects unsafe stored URL %s', (url) => expect(() => safeAvatarUrl(url)).toThrow())
it('accepts HTTPS image URLs and null current photos', () => {
  expect(safeAvatarUrl('https://images.example.test/photo.webp')).toBe('https://images.example.test/photo.webp')
  expect(validateAvatarProfile({ id: 'owner', avatar_url: null }, 'owner').avatar_url).toBeNull()
})
it('rejects foreign profile images', () => expect(() => validateAvatarProfile({ id: 'other', avatar_url: null }, 'owner')).toThrow())
