export const MAX_AVATAR_BYTES = 2 * 1024 * 1024
export function validateAvatarFile(file: Pick<File, 'size' | 'type'>) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG or WebP image.')
  if (file.size === 0 || file.size > MAX_AVATAR_BYTES) throw new Error('Choose a non-empty image no larger than 2 MiB.')
}
export function validateAvatarDimensions(width: number, height: number) {
  if (width <= 0 || height <= 0 || !Number.isSafeInteger(width * height) || width * height > 25_000_000) throw new Error('Choose an image no larger than 25 megapixels.')
}
export function safeAvatarUrl(value: unknown): string {
  if (typeof value !== 'string') throw new Error('The profile photo URL could not be verified.')
  try {
    const url = new URL(value)
    if (url.protocol === 'https:' && !url.username && !url.password) return url.href
  } catch { /* Report an invalid response without navigating to it. */ }
  throw new Error('The profile photo URL could not be verified.')
}
export interface AvatarProfile { id: string; avatar_url: string | null }
export function validateAvatarProfile(value: AvatarProfile, owner: string): AvatarProfile {
  if (!value || value.id !== owner || (value.avatar_url !== null && typeof value.avatar_url !== 'string')) throw new Error('Profile photo information could not be verified for this account.')
  return { id: value.id, avatar_url: value.avatar_url === null ? null : safeAvatarUrl(value.avatar_url) }
}
