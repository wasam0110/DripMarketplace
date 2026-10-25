import { isOrderId } from '../orders/api'
import { safeAvatarUrl } from '../account/avatar'

export interface ReviewPhotos { id: string; product_id: string; user: { id: string }; status: string; images: { id: string; url: string; sort_order: number }[] }
export function validatePhotoFile(file: Pick<File, 'size' | 'type'>) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size === 0 || file.size > 5 * 1024 * 1024) throw new Error('Choose a non-empty JPEG, PNG or WebP no larger than 5 MiB.')
}
export function validateReviewPhotos(value: ReviewPhotos, owner: string, id: string): ReviewPhotos {
  if (!value || value.id !== id || value.user?.id !== owner || !isOrderId(value.product_id)
    || !['pending', 'approved', 'rejected', 'hidden'].includes(value.status) || !Array.isArray(value.images)
    || new Set(value.images.map((image) => image?.id)).size !== value.images.length) throw new Error('Review photos could not be verified for your account.')
  for (const image of value.images) {
    if (!image || !isOrderId(image.id) || !Number.isInteger(image.sort_order) || image.sort_order < 0) throw new Error('Review photo information is incomplete.')
    safeAvatarUrl(image.url)
  }
  return value
}
export function confirmPhotoChange(before: ReviewPhotos, after: ReviewPhotos, deleted?: string): ReviewPhotos {
  const oldIds = before.images.map((image) => image.id), newIds = after.images.map((image) => image.id)
  if (before.id !== after.id || before.product_id !== after.product_id || after.status !== 'pending'
    || (deleted ? !oldIds.includes(deleted) || newIds.includes(deleted) || newIds.length !== oldIds.length - 1 || !newIds.every((id) => oldIds.includes(id))
      : newIds.length !== oldIds.length + 1 || !oldIds.every((id) => newIds.includes(id)))) throw new Error('The photo change could not be confirmed. Refresh and inspect before repeating it.')
  return after
}
