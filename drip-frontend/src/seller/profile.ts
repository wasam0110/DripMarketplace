import { isOrderId } from '../orders/api'

export const profileLimits = { description: 2000, return_policy: 1000, whatsapp_number: 20, instagram_handle: 100 } as const
export type BrandDraft = Record<keyof typeof profileLimits | 'brand_color', string>
export interface BrandProfile {
  id: string; brand_name: string; description: string | null; return_policy: string | null
  whatsapp_number: string | null; instagram_handle: string | null; brand_color: string
}
export function validateBrandProfile(value: BrandProfile): BrandProfile {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id)
    || typeof value.brand_name !== 'string' || !value.brand_name.trim()
    || typeof value.brand_color !== 'string' || !/^#[0-9a-f]{6}$/i.test(value.brand_color)
    || Object.entries(profileLimits).some(([key, limit]) => {
      const field = value[key as keyof typeof profileLimits]
      return field !== null && (typeof field !== 'string' || field.length > limit)
    })) throw new Error('The server returned incomplete brand details. Refresh before editing.')
  return { id: value.id, brand_name: value.brand_name, description: value.description,
    return_policy: value.return_policy, whatsapp_number: value.whatsapp_number,
    instagram_handle: value.instagram_handle, brand_color: value.brand_color }
}
export function brandDraft(profile: BrandProfile): BrandDraft {
  return { description: profile.description ?? '', return_policy: profile.return_policy ?? '',
    whatsapp_number: profile.whatsapp_number ?? '', instagram_handle: profile.instagram_handle ?? '', brand_color: profile.brand_color }
}
/** Whitelist editable fields; empty strings deliberately clear optional text, never send null. */
export function brandChanges(draft: BrandDraft, initial: BrandProfile): Partial<BrandDraft> {
  const baseline = brandDraft(initial)
  const changes: Partial<BrandDraft> = {}
  for (const key of Object.keys(baseline) as (keyof BrandDraft)[]) {
    const value = draft[key]
    if (typeof value !== 'string' || (key === 'brand_color' ? !/^#[0-9a-f]{6}$/i.test(value) : value.length > profileLimits[key])) {
      throw new Error('Check the field lengths and use a six-digit hex brand colour, such as #203C32.')
    }
    if (value !== baseline[key]) changes[key] = value
  }
  return changes
}
export function confirmBrandUpdate(value: BrandProfile, initial: BrandProfile, changes: Partial<BrandDraft>): BrandProfile {
  const confirmed = validateBrandProfile(value)
  if (confirmed.id !== initial.id || Object.entries(changes).some(([key, field]) => confirmed[key as keyof BrandDraft] !== field)) {
    throw new Error('The requested brand changes could not be confirmed. Inspect the server profile before making another change.')
  }
  return confirmed
}
