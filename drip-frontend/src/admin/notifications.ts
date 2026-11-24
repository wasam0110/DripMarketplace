import { isOrderId } from '../orders/api'
export interface FailedNotification { id: string; event_key: string; task_name: string; publication_attempts: number; delivery_attempts: number; last_error: string | null; dead_lettered_at: string; replay_history: unknown[] }
export interface FailedNotifications { page: number; data: FailedNotification[] }
export interface EmailLog { id: string; recipient_email: string; subject: string; template_id: string | null; status: string; resend_id: string | null; error_message: string | null; sent_at: string }
export interface EmailLogs { data: EmailLog[]; total: number; page: number }
export interface BroadcastResponse { recipient_count: number; task_id: string }
const fail = (): never => { throw new Error('Notification information could not be verified. Refresh to try again.') }
const text = (value: unknown): value is string => typeof value === 'string' && !!value.trim()
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const date = (value: unknown): value is string => typeof value === 'string' && Number.isFinite(Date.parse(value))
export function validateFailed(value: FailedNotifications, page: number) {
  if (!value || value.page !== page || !Array.isArray(value.data) || value.data.length > 100) return fail()
  for (const row of value.data) if (!row || !isOrderId(row.id) || !text(row.event_key) || !text(row.task_name) || !count(row.publication_attempts) || !count(row.delivery_attempts) || !(row.last_error === null || text(row.last_error)) || !date(row.dead_lettered_at) || !Array.isArray(row.replay_history)) return fail()
  return value
}
export function validateEmailLogs(value: EmailLogs, page: number) {
  if (!value || value.page !== page || !count(value.total) || !Array.isArray(value.data) || value.data.length > 25) return fail()
  for (const row of value.data) if (!row || !isOrderId(row.id) || !text(row.recipient_email) || !text(row.subject) || !(row.template_id === null || text(row.template_id)) || !text(row.status) || !(row.resend_id === null || text(row.resend_id)) || !(row.error_message === null || text(row.error_message)) || !date(row.sent_at)) return fail()
  return value
}
export function validateBroadcast(value: BroadcastResponse) {
  if (!value || !count(value.recipient_count) || !isOrderId(value.task_id)) return fail()
  return value
}
export const replayMarker = (owner: string, id: string) => `wearhowz:admin-notification-replay-pending:${owner}:${id}`
