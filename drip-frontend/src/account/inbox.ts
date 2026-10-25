export interface InboxItem { id: string; type: string; title: string; body: string; action_url: string | null; is_read: boolean; created_at: string }
export interface Inbox { data: InboxItem[]; unread_count: number; total: number; page: number }
const uuidPattern = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
const uuid = new RegExp(`^${uuidPattern}$`, 'i')
const count = (value: unknown) => Number.isSafeInteger(value) && (value as number) >= 0
export function validateInbox(value: Inbox, page: number): Inbox {
  if (!value || !Array.isArray(value.data) || value.data.length > 20 || value.page !== page || !count(value.total) || !count(value.unread_count) || value.data.length > value.total ||
    value.data.some((item) => !item || typeof item.id !== 'string' || !uuid.test(item.id) || ![item.type, item.title, item.body, item.created_at].every((field) => typeof field === 'string') ||
      !Number.isFinite(Date.parse(item.created_at)) || typeof item.is_read !== 'boolean' || (item.action_url !== null && typeof item.action_url !== 'string')) ||
    new Set(value.data.map((item) => item.id)).size !== value.data.length) throw new Error('Notification information could not be verified. Refresh your inbox.')
  return value
}
// Never navigate notification-supplied external URLs, API routes, credentials or query strings.
export function notificationLink(value: string | null): string | null {
  if (!value) return null
  if (['/orders', '/clothing', '/brands', '/saved', '/account/reviews'].includes(value)) return value
  return new RegExp(`^/(orders|products)/${uuidPattern}$`, 'i').test(value) ? value : null
}
