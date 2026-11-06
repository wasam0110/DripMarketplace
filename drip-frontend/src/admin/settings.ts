export const settingFields = [
  { key: 'commission_rate', label: 'Commission rate (0–1)', hint: '0.15 means 15%. Allowed range: 0 to 1.', min: 0, max: 1, integer: false },
  { key: 'registration_fee', label: 'Seller registration fee (PKR)', hint: 'Whole rupees. Zero permits free registration.', min: 0, max: Number.MAX_SAFE_INTEGER, integer: true },
  { key: 'extra_slot_price', label: 'Extra product slot price (PKR)', hint: 'Whole rupees per extra slot; zero is allowed.', min: 0, max: Number.MAX_SAFE_INTEGER, integer: true },
  { key: 'free_shipping_threshold', label: 'Free shipping threshold (PKR)', hint: 'Whole rupees. Review the effect on shipping before using zero.', min: 0, max: Number.MAX_SAFE_INTEGER, integer: true },
  { key: 'standard_shipping_fee', label: 'Standard shipping fee (PKR)', hint: 'Whole rupees; zero means no standard shipping charge.', min: 0, max: Number.MAX_SAFE_INTEGER, integer: true },
  { key: 'cod_timeout_minutes', label: 'COD decision timeout (minutes)', hint: '5–1440 minutes. Changes can affect expiry processing.', min: 5, max: 1440, integer: true },
  { key: 'wallet_hold_days', label: 'Seller wallet hold (days)', hint: '0–30 days. Review the effect on settlement release before reducing it.', min: 0, max: 30, integer: true },
] as const
export type SettingKey = typeof settingFields[number]['key']
export type PlatformSettings = Record<SettingKey, number>
export type SettingsDraft = Record<SettingKey, string>
export function validateSettings(v: PlatformSettings): PlatformSettings {
  if (!v || typeof v !== 'object') throw new Error('Platform settings could not be verified.')
  for (const f of settingFields) {
    const n = v[f.key]
    if (typeof n !== 'number' || !Number.isFinite(n) || n < f.min || n > f.max || f.integer && !Number.isSafeInteger(n)) throw new Error(`Invalid saved ${f.label.toLowerCase()}. No changes are available.`)
  }
  return Object.fromEntries(settingFields.map(f => [f.key, v[f.key]])) as PlatformSettings
}
export const settingsDraft = (v: PlatformSettings) => Object.fromEntries(settingFields.map(f => [f.key, String(v[f.key])])) as SettingsDraft
export const sameSettings = (a: PlatformSettings, b: PlatformSettings) => settingFields.every(f => a[f.key] === b[f.key])
export function settingsPayload(before: PlatformSettings, draft: SettingsDraft, checked: boolean) {
  validateSettings(before)
  if (!checked) throw new Error('Acknowledge the effect of these platform-wide changes.')
  const changes: Partial<PlatformSettings> = {}
  for (const f of settingFields) {
    const text = draft[f.key].trim(), n = Number(text)
    if (!(f.integer ? /^\d+$/ : /^(?:\d+(?:\.\d+)?|\.\d+)$/).test(text) || !Number.isFinite(n) || n < f.min || n > f.max || f.integer && !Number.isSafeInteger(n)) throw new Error(`Enter a valid ${f.label.toLowerCase()}. ${f.hint}`)
    if (n !== before[f.key]) changes[f.key] = n
  }
  if (!Object.keys(changes).length) throw new Error('Change at least one setting before reviewing.')
  return { ...changes, expected_settings: before }
}
export function confirmSettings(v: PlatformSettings, body: ReturnType<typeof settingsPayload>) {
  const saved = validateSettings(v), { expected_settings, ...changes } = body
  if (!sameSettings(saved, { ...expected_settings, ...changes })) throw new Error('Saved settings do not match the reviewed changes. Inspect current settings before another action.')
  return saved
}
export const settingsMarker = (owner: string) => `wearhowz:admin-settings-pending:${owner}`
