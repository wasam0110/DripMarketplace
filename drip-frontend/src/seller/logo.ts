import { isOrderId } from '../orders/api'
export interface SellerLogo { id: string; brand_name: string; logo_url: string | null }
export function safeLogoUrl(value: unknown): string {
  if (typeof value === 'string') {
    try {
      const url = new URL(value)
      if (url.protocol === 'https:' && !url.username && !url.password) return url.href
    } catch { /* An untrusted response must not become an image source. */ }
  }
  throw new Error('The logo URL could not be verified.')
}
export function validateSellerLogo(value: SellerLogo): SellerLogo {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id)
    || typeof value.brand_name !== 'string' || !value.brand_name.trim()) throw new Error('Seller logo details could not be verified.')
  return { id: value.id, brand_name: value.brand_name, logo_url: value.logo_url === null ? null : safeLogoUrl(value.logo_url) }
}
export function confirmSellerLogo(value: SellerLogo, sellerId: string, uploadedUrl: string) {
  const profile = validateSellerLogo(value)
  if (profile.id !== sellerId || profile.logo_url !== uploadedUrl) throw new Error('The saved logo could not be confirmed. Inspect the saved profile before uploading again.')
  return profile
}
