import { isOrderId } from '../orders/api'
import { moderationImage } from './products'

export const bannerPositions = { homepage_hero: 'Homepage hero', homepage_secondary: 'Homepage secondary', category_top: 'Category top' } as const
export interface AdminBanner { id: string; title: string; image_url: string; link_url: string | null; position: keyof typeof bannerPositions; sort_order: number; is_active: boolean; valid_from: string | null; valid_until: string | null; created_at: string; updated_at: string }
export interface BannerDraft { title: string; link: string; position: string; order: string; active: boolean; start: string; end: string }
const fail = (): never => { throw new Error('Banner information could not be verified. Refresh to try again.') }
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
export function validateBanner(value: AdminBanner) {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id) || typeof value.title !== 'string' || !value.title.trim() || typeof value.image_url !== 'string' || !value.image_url || !(value.link_url === null || typeof value.link_url === 'string')
    || !Object.hasOwn(bannerPositions, value.position) || !Number.isSafeInteger(value.sort_order) || value.sort_order < 0 || value.sort_order > 2147483647 || typeof value.is_active !== 'boolean'
    || !date(value.created_at) || !date(value.updated_at) || ![value.valid_from, value.valid_until].every((v) => v === null || date(v))) return fail()
  if (value.valid_from && value.valid_until && Date.parse(value.valid_until) <= Date.parse(value.valid_from)) return fail()
  return value
}
export function validateBanners(value: AdminBanner[]) {
  if (!Array.isArray(value)) return fail()
  const ids = new Set<string>(); for (const row of value) { validateBanner(row); if (ids.has(row.id)) return fail(); ids.add(row.id) }; return value
}
export function bannerLink(value: string): string | null {
  const link = value.trim(); if (!link) return null
  if (/[\s\u0000-\u001f\u007f\\]/.test(link)) throw new Error('Use an HTTPS or site-relative banner link without spaces or backslashes.')
  if (link.startsWith('/') && !link.startsWith('//')) return link
  try { const url = new URL(link); if (url.protocol === 'https:' && url.hostname && !url.username && !url.password) return link } catch { /* Fail closed. */ }
  throw new Error('Use an HTTPS or site-relative banner link without embedded credentials.')
}
export const utcInput = (value: string | null) => value ? new Date(value).toISOString().slice(0, 16) : ''
export function bannerDraft(row?: AdminBanner): BannerDraft {
  return { title: row?.title ?? '', link: row?.link_url ?? '', position: row?.position ?? 'homepage_hero', order: String(row?.sort_order ?? 0), active: row?.is_active ?? false, start: utcInput(row?.valid_from ?? null), end: utcInput(row?.valid_until ?? null) }
}
function schedule(value: string, previous: string | null) {
  if (!value) return null
  if (previous && utcInput(previous) === value) return previous
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('Enter valid UTC schedule dates.')
  const parsed = new Date(`${value}:00Z`)
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 16) !== value) throw new Error('Enter valid UTC schedule dates.')
  return parsed.toISOString()
}
export function bannerPayload(draft: BannerDraft, before?: AdminBanner) {
  const title = draft.title.trim()
  if (!title || title.length > 200 || draft.link.length > 500 || !Object.hasOwn(bannerPositions, draft.position) || !/^\d+$/.test(draft.order) || !Number.isSafeInteger(Number(draft.order)) || Number(draft.order) > 2147483647) throw new Error('Use a title of 1–200 characters, a valid position and a non-negative 32-bit sort order.')
  const fields = { title, link_url: bannerLink(draft.link), position: draft.position as AdminBanner['position'], sort_order: Number(draft.order), is_active: draft.active }
  const valid_from = before ? schedule(draft.start, before.valid_from) : null, valid_until = before ? schedule(draft.end, before.valid_until) : null
  if (valid_from && valid_until && Date.parse(valid_until) <= Date.parse(valid_from)) throw new Error('Banner end must follow its start.')
  const payload = { ...fields, valid_from, valid_until }
  if (before && Object.entries(payload).every(([key, value]) => value === before[key as keyof AdminBanner])) throw new Error('Change a banner field before reviewing.')
  return payload
}
export function sameBanner(before: AdminBanner, latest: AdminBanner) {
  const snapshot = (row: AdminBanner) => [row.id, row.title, row.image_url, row.link_url, row.position, row.sort_order, row.is_active, row.valid_from, row.valid_until, row.updated_at]
  return JSON.stringify(snapshot(before)) === JSON.stringify(snapshot(latest))
}
export function confirmBanner(value: AdminBanner, payload: ReturnType<typeof bannerPayload>, before?: AdminBanner) {
  validateBanner(value)
  if (!moderationImage(value.image_url) || (before && (value.id !== before.id || value.image_url !== before.image_url || value.updated_at === before.updated_at))) return fail()
  for (const [key, field] of Object.entries(payload)) {
    const saved = value[key as keyof AdminBanner]
    if (key === 'valid_from' || key === 'valid_until') { if (!(saved === field || (typeof saved === 'string' && typeof field === 'string' && Date.parse(saved) === Date.parse(field)))) return fail() }
    else if (saved !== field) return fail()
  }
  return value
}
export function validateBannerFile(file: Pick<File, 'size' | 'type'>) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size <= 0 || file.size > 5 * 1024 * 1024) throw new Error('Choose a non-empty JPEG, PNG or WebP image up to 5 MiB.')
}
export const bannerMarker = (owner: string, id: string) => `wearhowz:admin-banner-pending:${owner}:${id}`
