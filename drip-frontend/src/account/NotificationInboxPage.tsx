import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { request } from '../api/client'
import { Button, ErrorNotice } from '../components/ui'
import { orderDate, useOrderRead } from '../orders/api'
import { AccountGate, useAccountWrite, WriteFeedback } from './AccountDetails'
import { notificationLink, validateInbox, type Inbox, type InboxItem } from './inbox'

export function NotificationInboxPage() {
  return <AccountGate title="Your notifications">{(owner) => <InboxManager key={owner} />}</AccountGate>
}
function InboxManager() {
  const [page, setPage] = useState(1)
  const [unread, setUnread] = useState(false)
  const [confirmAll, setConfirmAll] = useState(false)
  const [result, setResult] = useState('')
  const validate = useCallback((value: Inbox) => validateInbox(value, page), [page])
  const resource = useOrderRead(`/notifications?page=${page}&per_page=20&unread_only=${unread}`, true, validate)
  const write = useAccountWrite()
  const disabled = write.busy || write.blocked || resource.loading || !resource.data
  function refresh() { setConfirmAll(false); resource.retry() }
  function mark(item?: InboxItem) {
    if (disabled) return
    setResult('')
    void write.run(async () => {
      if (item) {
        const response = await request<{ marked: boolean }>(`/notifications/${item.id}/read`, { method: 'POST', authenticated: true })
        if (!response || typeof response.marked !== 'boolean') throw new Error('Read status could not be confirmed.')
        return response.marked ? 'Notification marked as read.' : 'This notification was not found for your account. The inbox has been refreshed.'
      }
      const response = await request<{ updated_count: number }>('/notifications/read-all', { method: 'POST', authenticated: true })
      if (!response || !Number.isSafeInteger(response.updated_count) || response.updated_count < 0) throw new Error('Bulk read status could not be confirmed.')
      return `Server marked ${response.updated_count} notifications as read, including any archived notifications affected.`
    }, (message) => { setResult(message); refresh() }, '')
  }
  return <>
    <p>Opening a notification or its linked page does not mark it as read automatically. Counts reflect the last server refresh, not live updates.</p>
    <p><Link className="text-link" to="/account/notifications">Manage notification preferences</Link></p>
    <label className="checkbox-label"><input type="checkbox" checked={unread} disabled={write.busy || resource.loading} onChange={(event) => { setUnread(event.target.checked); setPage(1); setConfirmAll(false); setResult('') }} />Show unread only</label>
    {resource.loading && <p role="status">Loading notifications…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} /><p role="status">{result}</p>
    {resource.data && <>
      <p>{resource.data.unread_count} unread notifications (when loaded)</p>
      <p>{resource.data.total} {unread ? 'unread' : 'active'} notifications in this view</p>
      {!resource.data.data.length && <p>{page > 1 ? 'No notifications on this page. Return to the previous page.' : unread ? 'No unread notifications.' : 'Your inbox is empty.'}</p>}
      {resource.data.data.map((item) => {
        const link = notificationLink(item.action_url)
        return <article className="account-card" key={item.id}>
          <p className="eyebrow">{item.is_read ? 'Read' : 'Unread'} · {orderDate(item.created_at)}</p>
          <h2>{item.title}</h2><p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.body}</p>
          {link && <p><Link className="text-link" to={link}>View related page</Link></p>}
          {item.action_url && !link && <p className="muted">The linked destination is not supported here.</p>}
          {!item.is_read && <Button className="button-secondary" disabled={Boolean(disabled)} onClick={() => mark(item)} aria-label={`Mark ${item.title} as read`}>Mark as read</Button>}
        </article>
      })}
      <nav className="pagination" aria-label="Notification pages">
        <Button className="button-secondary" disabled={write.busy || page === 1} onClick={() => { setPage((value) => value - 1); setConfirmAll(false) }}>Previous notifications</Button>
        <span>Page {page}</span><Button className="button-secondary" disabled={write.busy || page * 20 >= resource.data.total} onClick={() => { setPage((value) => value + 1); setConfirmAll(false) }}>Next notifications</Button>
      </nav>
      {!confirmAll ? <Button disabled={Boolean(disabled) || resource.data.unread_count === 0} onClick={() => setConfirmAll(true)}>Mark all as read</Button> : <div className="notice">
        <p>Mark every unread notification in your account as read, including other pages and archived notifications? This cannot be undone here.</p>
        <Button disabled={Boolean(disabled)} onClick={() => mark()}>Yes, mark all as read</Button>{' '}
        <Button className="button-secondary" disabled={write.busy} onClick={() => setConfirmAll(false)}>Keep unread notifications</Button>
      </div>}
    </>}
    <Button className="button-secondary" disabled={write.busy || resource.loading} onClick={refresh}>Refresh inbox</Button>
    {!resource.data && page > 1 && <Button className="button-secondary" disabled={write.busy || resource.loading} onClick={() => setPage((value) => value - 1)}>Previous notifications</Button>}
  </>
}
