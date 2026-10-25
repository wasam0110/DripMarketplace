import { expect, it } from 'vitest'
import { confirmPhotoChange, validatePhotoFile, validateReviewPhotos } from './photos'
const id = '11111111-1111-4111-8111-111111111111'
const image = { id, url: 'https://images.example.test/photo.webp', sort_order: 0 }
const review = { id, product_id: id, user: { id: 'owner' }, status: 'approved', images: [] as typeof image[] }
it('accepts only bounded non-empty image files', () => {
  expect(() => validatePhotoFile({ size: 10, type: 'image/png' })).not.toThrow()
  for (const file of [{ size: 0, type: 'image/png' }, { size: 5 * 1024 * 1024 + 1, type: 'image/png' }, { size: 10, type: 'image/svg+xml' }]) expect(() => validatePhotoFile(file)).toThrow()
})
it('validates ownership, unique photos and safe URLs', () => {
  expect(validateReviewPhotos(review, 'owner', id)).toBe(review)
  expect(() => validateReviewPhotos(review, 'other', id)).toThrow()
  expect(() => validateReviewPhotos({ ...review, images: [image, image] }, 'owner', id)).toThrow()
  expect(() => validateReviewPhotos({ ...review, images: [{ ...image, url: 'javascript:alert(1)' }] }, 'owner', id)).toThrow()
})
it('confirms exact add/remove changes and pending moderation', () => {
  const added = { ...review, status: 'pending', images: [image] }
  expect(confirmPhotoChange(review, added)).toBe(added)
  expect(confirmPhotoChange(added, { ...review, status: 'pending' }, id).images).toEqual([])
  expect(() => confirmPhotoChange(review, review)).toThrow()
  expect(() => confirmPhotoChange(review, { ...added, status: 'approved' })).toThrow()
  expect(() => confirmPhotoChange(added, added, id)).toThrow()
})
