import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { confirmSettings, sameSettings, settingFields, settingsDraft, settingsMarker, settingsPayload, validateSettings, type PlatformSettings } from './settings'
import './products.css'

export function AdminSettingsPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Platform settings</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage settings</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Runtime policy</p><h1>Platform settings</h1><p>These settings affect marketplace pricing, shipping and operational timing. Review every change before saving.</p><p>This screen does not configure API keys, enable payment providers or rewrite historical orders. Existing records and scheduled jobs may use different saved or runtime rules.</p><SettingsManager key={user.id} owner={user.id} /></section>
}
const path = '/admin/settings'
function SettingsManager({ owner }: { owner: string }) {
  const resource = useOrderRead(path, true, validateSettings), write = useAccountWrite(), active = useRef(false), marker = settingsMarker(owner)
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(marker) !== null } catch { return true } })
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  function save(body: ReturnType<typeof settingsPayload>) {
    if (pending || write.busy || write.blocked || resource.loading) return
    void write.run(async () => {
      let sent = false
      try {
        const latest = validateSettings(await request<PlatformSettings>(path, { authenticated: true, cache: 'no-store' }))
        if (!active.current) throw new Error('The review session changed. No settings were sent.')
        if (!sameSettings(latest, body.expected_settings)) { resource.retry(); throw new Error('Platform settings changed. Review the refreshed values.') }
        sessionStorage.setItem(marker, 'pending'); setPending(true); sent = true
        const receipt = await request<PlatformSettings>(path, { authenticated: true, method: 'PATCH', body: JSON.stringify(body) })
        try {
          confirmSettings(receipt, body)
          confirmSettings(await request<PlatformSettings>(path, { authenticated: true, cache: 'no-store' }), body)
        } catch { throw new Error('The settings outcome could not be confirmed. Inspect saved values before another change.') }
        sessionStorage.removeItem(marker); setPending(false)
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'Settings could not be rechecked. Nothing was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(marker); setPending(false); resource.retry() }
        throw reason
      }
    }, resource.retry, 'Platform settings saved and verified.')
  }
  return <>{resource.loading && <p role="status">Loading effective settings...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={write} />{pending && !write.busy && <p role="alert">A settings update is awaiting confirmation. Inspect saved values or contact support before repeating it.</p>}{resource.data && <SettingsForm key={JSON.stringify(resource.data)} value={resource.data} disabled={resource.loading || write.busy || write.blocked || pending} save={save} />}<Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh settings and discard draft</Button></>
}
function SettingsForm({ value, disabled, save }: { value: PlatformSettings; disabled: boolean; save: (body: ReturnType<typeof settingsPayload>) => void }) {
  const [draft, setDraft] = useState(() => settingsDraft(value)), [checked, setChecked] = useState(false), [error, setError] = useState<unknown>(null), [review, setReview] = useState<ReturnType<typeof settingsPayload> | null>(null), panel = useRef<HTMLDivElement>(null)
  useEffect(() => { if (review) panel.current?.focus() }, [review])
  return <form className="account-card auth-form" onSubmit={e => { e.preventDefault(); if (disabled || review) return; try { setReview(settingsPayload(value, draft, checked)); setError(null) } catch (reason) { setError(reason) } }}><h2>Effective business settings</h2><p>Values include stored overrides and configured defaults. Only changed fields will be saved; there is no reset-to-default action here.</p>{settingFields.map(f => <Field key={f.key} label={f.label} hint={f.hint} value={draft[f.key]} inputMode={f.integer ? 'numeric' : 'decimal'} maxLength={24} disabled={disabled || !!review} onChange={e => { setDraft({ ...draft, [f.key]: e.target.value }); setChecked(false) }} />)}<label><input type="checkbox" checked={checked} disabled={disabled || !!review} onChange={e => setChecked(e.target.checked)} /> I reviewed the platform-wide pricing and timing effects of these changes.</label>{Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review settings changes</Button>{review && <div className="admin-product-confirm" ref={panel} tabIndex={-1} aria-label="Confirm settings changes"><h3>Save these platform settings?</h3><dl>{settingFields.filter(f => f.key in review).map(f => <div key={f.key}><dt>{f.label}</dt><dd>{value[f.key]} → {review[f.key]}</dd></div>)}</dl><p>Only the changes above will be written. This takes effect as runtime consumers read the saved policy; it is not a scheduled deployment.</p><div className="option-row"><Button disabled={disabled} onClick={() => save(review)}>Confirm settings update</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to settings draft</Button></div></div>}</form>
}
