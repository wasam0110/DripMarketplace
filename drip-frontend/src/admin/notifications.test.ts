import { expect, it } from 'vitest'
import { validateBroadcast, validateEmailLogs, validateFailed } from './notifications'
const id = '11111111-1111-4111-8111-111111111111'
it('validates failed notification pages and replay-safe fields', () => {
  const value = { page: 1, data: [{ id, event_key: 'order:1', task_name: 'send_order', publication_attempts: 2, delivery_attempts: 3, last_error: 'timeout', dead_lettered_at: '2026-11-24T10:00:00Z', replay_history: [] }] }
  expect(validateFailed(value, 1)).toBe(value)
  expect(() => validateFailed({ ...value, page: 2 }, 1)).toThrow()
  expect(() => validateFailed({ ...value, data: [{ ...value.data[0], id: 'bad' }] }, 1)).toThrow()
})
it('validates email logs and broadcast acknowledgements', () => {
  const logs = { page: 1, total: 1, data: [{ id, recipient_email: 'a@example.test', subject: 'Order', template_id: null, status: 'failed', resend_id: null, error_message: 'timeout', sent_at: '2026-11-24T10:00:00Z' }] }
  expect(validateEmailLogs(logs, 1)).toBe(logs)
  expect(validateBroadcast({ recipient_count: 2, task_id: id }).recipient_count).toBe(2)
  expect(() => validateBroadcast({ recipient_count: 2, task_id: 'bad' })).toThrow()
})
