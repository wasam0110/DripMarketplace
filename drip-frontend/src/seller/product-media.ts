import { isOrderId } from '../orders/api'
import { safeAvatarUrl } from '../account/avatar'
import { validateOptions, type OptionsProduct } from './product-options'

export interface ProductImage { id: string; url: string; alt_text: string | null; sort_order: number; is_primary: boolean }
export interface MediaProduct extends OptionsProduct { images: ProductImage[]; is_published: boolean }
export function validateProductImages(images: ProductImage[]) {
  if (!Array.isArray(images) || images.length > 6) throw new Error('The product image list could not be verified.')
  const ids = new Set<string>()
  for (const row of images) {
    if (!row || typeof row.id !== 'string' || !isOrderId(row.id) || ids.has(row.id)
      || !(row.alt_text === null || typeof row.alt_text === 'string')
      || !Number.isSafeInteger(row.sort_order) || row.sort_order < 0 || typeof row.is_primary !== 'boolean') throw new Error('The product image details could not be verified.')
    safeAvatarUrl(row.url); ids.add(row.id)
  }
  if (images.filter((row) => row.is_primary).length > 1) throw new Error('Multiple primary images were returned. Inspect the product before editing.')
  return [...images].sort((a, b) => a.sort_order - b.sort_order || a.id.localeCompare(b.id))
}
export function validateMedia(value: MediaProduct, seller: string, id: string): MediaProduct {
  validateOptions(value, seller, id)
  if (typeof value.is_published !== 'boolean') throw new Error('Publication status is unavailable. Update the backend before using these controls.')
  return { ...value, images: validateProductImages(value.images) }
}
export function validateProductFile(file: Pick<File, 'size' | 'type'>) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size <= 0 || file.size > 5 * 1024 * 1024) throw new Error('Choose a non-empty JPEG, PNG or WebP image up to 5 MiB.')
}
export function movedImageIds(images: ProductImage[], id: string, direction: -1 | 1) {
  const ids = images.map((row) => row.id), index = ids.indexOf(id), next = index + direction
  if (index < 0 || next < 0 || next >= ids.length) throw new Error('This image cannot move in that direction.')
  ;[ids[index], ids[next]] = [ids[next], ids[index]]
  return ids
}
