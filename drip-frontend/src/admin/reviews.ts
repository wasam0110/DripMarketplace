import { isOrderId } from '../orders/api'

export const reviewStatuses = ['pending', 'approved', 'rejected', 'hidden'] as const
export type ReviewStatus = typeof reviewStatuses[number]
export type ReviewDecision = Exclude<ReviewStatus, 'pending'>
export interface AdminReview {
  id: string; product_id: string; user: { id: string; first_name: string | null; last_name: string | null; avatar_url: string | null }
  rating: number; title: string | null; body: string | null; status: ReviewStatus; is_verified_purchase: boolean
  helpful_count: number; unhelpful_count: number; images: { id: string; url: string; sort_order: number }[]
  admin_note: string | null; moderated_at: string | null; created_at: string; updated_at: string
}
export interface AdminReviews { data: AdminReview[]; total: number; page: number; per_page: number }
const fail = (): never => { throw new Error('Review moderation information could not be verified. Refresh to try again.') }
const nullable = (v: unknown) => v === null || typeof v === 'string'
const uuid = (v: unknown): v is string => typeof v === 'string' && isOrderId(v)
const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
export function reviewQuery(status: string, page: string) {
  if (!(status === 'all' || reviewStatuses.some((value) => value === status)) || !/^[1-9]\d*$/.test(page) || !Number.isSafeInteger(Number(page))) throw new Error('Choose a valid review status and positive page number.')
  const params = new URLSearchParams({ page }); if (status !== 'all') params.set('status', status); return params.toString()
}
export function validateAdminReview(value: AdminReview, id?: string) {
  if (!value || !uuid(value.id) || (id !== undefined && value.id !== id) || !uuid(value.product_id) || !value.user || !uuid(value.user.id)
    || ![value.user.first_name, value.user.last_name, value.user.avatar_url, value.title, value.body, value.admin_note].every(nullable)
    || !reviewStatuses.includes(value.status) || !Number.isInteger(value.rating) || value.rating < 1 || value.rating > 5 || typeof value.is_verified_purchase !== 'boolean'
    || !count(value.helpful_count) || !count(value.unhelpful_count) || !date(value.created_at) || !date(value.updated_at) || !(value.moderated_at === null || date(value.moderated_at)) || !Array.isArray(value.images)) return fail()
  const ids = new Set<string>()
  for (const image of value.images) { if (!image || !uuid(image.id) || ids.has(image.id) || typeof image.url !== 'string' || !count(image.sort_order)) return fail(); ids.add(image.id) }
  return value
}
export function validateAdminReviews(value: AdminReviews, page: number, status: string) {
  if (!value || !Array.isArray(value.data) || value.page !== page || value.per_page !== 25 || !count(value.total) || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateAdminReview(row); if (ids.has(row.id) || (status !== 'all' && row.status !== status)) return fail(); ids.add(row.id) }
  return value
}
export function reviewPayload(status: string, note: string, before: AdminReview) {
  if (!['approved', 'rejected', 'hidden'].includes(status) || note.length > 1000) throw new Error('Choose a moderation decision and a note of at most 1,000 characters.')
  const admin_note = note.trim() || null
  if (status === before.status && admin_note === before.admin_note) throw new Error('Change the decision or private note before reviewing.')
  return { status: status as ReviewDecision, admin_note, expected_updated_at: before.updated_at }
}
/** Votes are live counters; content, author, status and version must still match. */
export function sameReview(before: AdminReview, latest: AdminReview) {
  const snapshot = ({ helpful_count: _helpful, unhelpful_count: _unhelpful, images, ...row }: AdminReview) => ({ ...row, images: [...images].sort((a, b) => a.id.localeCompare(b.id)) })
  return JSON.stringify(snapshot(before)) === JSON.stringify(snapshot(latest))
}
export function confirmReview(value: AdminReview, before: AdminReview, payload: ReturnType<typeof reviewPayload>) {
  validateAdminReview(value, before.id)
  if (value.product_id !== before.product_id || value.user.id !== before.user.id || value.status !== payload.status || value.admin_note !== payload.admin_note || value.moderated_at === null || value.updated_at === before.updated_at) return fail()
  return value
}
export const reviewMarker = (owner: string, id: string) => `wearhowz:admin-review-pending:${owner}:${id}`
