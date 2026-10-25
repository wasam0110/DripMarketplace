export const preferenceFields = {
  email_order_updates: 'Order updates by email',
  email_promotions: 'Promotions by email',
  email_new_arrivals: 'New arrivals by email',
  sms_order_updates: 'Order updates by SMS',
  whatsapp_order_updates: 'Order updates by WhatsApp',
} as const
export type Preferences = Record<keyof typeof preferenceFields, boolean>
export const preferenceKeys = Object.keys(preferenceFields) as (keyof Preferences)[]
export function validatePreferences(value: Preferences): Preferences {
  if (!value || preferenceKeys.some((key) => typeof value[key] !== 'boolean')) throw new Error('Notification preferences could not be verified. Refresh before making changes.')
  return Object.fromEntries(preferenceKeys.map((key) => [key, value[key]])) as Preferences
}
export function changedPreferences(initial: Preferences, draft: Preferences): Partial<Preferences> {
  validatePreferences(initial); validatePreferences(draft)
  return Object.fromEntries(preferenceKeys.filter((key) => initial[key] !== draft[key]).map((key) => [key, draft[key]]))
}
