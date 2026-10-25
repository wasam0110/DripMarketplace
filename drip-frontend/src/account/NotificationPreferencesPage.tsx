import { useState } from 'react'
import { request } from '../api/client'
import { Button, ErrorNotice } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { AccountGate, useAccountWrite, WriteFeedback } from './AccountDetails'
import { changedPreferences, preferenceFields, preferenceKeys, validatePreferences, type Preferences } from './preferences'

export function NotificationPreferencesPage() {
  return <AccountGate title="Notification preferences">{(owner) => <PreferencesManager key={owner} />}</AccountGate>
}
function PreferencesManager() {
  const resource = useOrderRead('/me/notification-preferences', true, validatePreferences)
  const write = useAccountWrite()
  return <>
    <p>Choose the notification preferences saved for your account. Changes take effect only after you save.</p>
    <p className="notice">These settings record your choices; they do not verify that email, SMS or WhatsApp delivery is available. Saving does not send a test message. This is not a switch for all account or security messages.</p>
    {resource.loading && <p role="status">Loading notification preferences…</p>}
    {Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <PreferencesForm initial={resource.data} disabled={write.busy || write.blocked} save={(changes) => void write.run(async () => {
      const confirmed = validatePreferences(await request<Preferences>('/me/notification-preferences', { authenticated: true, method: 'PATCH', body: JSON.stringify(changes) }))
      if (preferenceKeys.some((key) => key in changes && confirmed[key] !== changes[key])) throw new Error('The requested preference changes could not be confirmed.')
      return confirmed
    }, () => resource.retry(), 'Notification preferences saved.')} />}
    <p className="muted">Refreshing discards unsaved choices and loads the server settings. Navigating away or signing out also discards this draft.</p>
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh notification preferences</Button>
  </>
}
function PreferencesForm({ initial, disabled, save }: { initial: Preferences; disabled: boolean; save: (changes: Partial<Preferences>) => void }) {
  const [draft, setDraft] = useState(initial)
  const changes = changedPreferences(initial, draft)
  const changed = Object.keys(changes).length > 0
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (!disabled && changed) save(changes) }}>
    <h2>Your notification choices</h2>
    {preferenceKeys.map((key) => <label className="checkbox-label" key={key}>
      <input type="checkbox" disabled={disabled} checked={draft[key]} onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })} />{preferenceFields[key]}
    </label>)}
    <p role="status">{changed ? 'You have unsaved changes.' : 'Showing your saved preferences.'}</p>
    <Button type="submit" disabled={disabled || !changed}>Save notification preferences</Button>
    <Button className="button-secondary" disabled={disabled || !changed} onClick={() => setDraft(initial)}>Discard preference changes</Button>
  </form>
}
