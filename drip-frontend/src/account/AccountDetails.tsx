import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { addressPayload, profileChanges, validateAddress, validateAddresses, validateProfile, type Address, type AddressDraft, type Profile, type ProfileDraft } from './contracts'

// A mounted private screen never replays a write whose outcome is unknown.
export function useAccountWrite() {
  const lock = useRef(false)
  const active = useRef(false)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  async function run<T>(operation: () => Promise<T>, confirmed: (result: T) => void, message: string) {
    if (lock.current || blocked) return
    lock.current = true; setBusy(true); setError(null); setNotice('')
    try {
      const result = await operation()
      if (active.current) { confirmed(result); setNotice(message) }
    } catch (reason) {
      if (active.current) {
        setError(reason)
        if (!(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500) setBlocked(true)
      }
    } finally { lock.current = false; if (active.current) setBusy(false) }
  }
  return { busy, blocked, error, notice, run }
}
export function WriteFeedback({ state }: { state: ReturnType<typeof useAccountWrite> }) {
  return <>{state.busy && <p role="status">Saving your change…</p>}{Boolean(state.error) && <ErrorNotice error={state.error} />}
    {state.blocked && <p className="notice" role="alert">The change could not be confirmed. Further changes are locked on this page. Refresh to inspect server data; do not repeat the change until its outcome is resolved.</p>}
    <p role="status">{state.notice}</p></>
}
export function AccountGate({ title, children }: { title: string; children: (owner: string) => ReactNode }) {
  const auth = useAuth()
  if (auth.loading) return <section className="container page" role="status">Checking your session…</section>
  if (!auth.user || auth.error) return <section className="container page"><h1>{title}</h1><p>Sign in to manage your account.</p><Link className="button" to="/login">Sign in</Link></section>
  return <section className="container page"><Link className="text-link" to="/account">Back to account</Link><h1>{title}</h1>{children(auth.user.id)}</section>
}
export function ProfilePage() { return <AccountGate title="Your profile">{(owner) => <ProfileManager key={owner} owner={owner} />}</AccountGate> }
function ProfileManager({ owner }: { owner: string }) {
  const auth = useAuth()
  const validate = useCallback((value: Profile) => validateProfile(value, owner), [owner])
  const resource = useOrderRead('/me', true, validate)
  const write = useAccountWrite()
  return <>
    <p>Update your name and Pakistani mobile number. Email changes are not supported here. Password and profile photo changes have separate account screens.</p>
    <p><Link className="text-link" to="/account/photo">Manage your profile photo</Link></p>
    {resource.loading && <p role="status">Loading your profile…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <ProfileForm initial={resource.data} disabled={write.busy || write.blocked} save={(changes) => void write.run(async () => {
      const result = validate(await request<Profile>('/me', { authenticated: true, method: 'PATCH', body: JSON.stringify(changes) }))
      if (Object.entries(changes).some(([key, value]) => result[key as keyof Profile] !== value)) throw new Error('The profile update could not be confirmed.')
      return result
    }, (result) => { auth.updateProfileNames(result); resource.retry() }, 'Profile updated.')} />}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh profile</Button>
  </>
}
function ProfileForm({ initial, disabled, save }: { initial: Profile; disabled: boolean; save: (value: Partial<ProfileDraft>) => void }) {
  const [draft, setDraft] = useState<ProfileDraft>({ first_name: initial.first_name ?? '', last_name: initial.last_name ?? '', phone: initial.phone ?? '' })
  const [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => {
    event.preventDefault(); if (disabled) return
    try { const changes = profileChanges(draft, initial); if (!Object.keys(changes).length) throw new Error('Make a change before saving.'); setError(null); save(changes) } catch (reason) { setError(reason) }
  }}>
    <p>Email: {initial.email} · {initial.has_verified_email ? 'Verified' : 'Not verified'}</p>
    <p className="muted">Leave unchanged fields as they are. Existing values cannot be cleared through the current API.</p>
    <Field label="First name" autoComplete="given-name" value={draft.first_name} maxLength={100} disabled={disabled} onChange={(e) => setDraft({ ...draft, first_name: e.target.value })} />
    <Field label="Last name" autoComplete="family-name" value={draft.last_name} maxLength={100} disabled={disabled} onChange={(e) => setDraft({ ...draft, last_name: e.target.value })} />
    <Field label="Mobile number" type="tel" autoComplete="tel" value={draft.phone} maxLength={16} disabled={disabled} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} hint="Pakistani mobile number, such as 03001234567." />
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled}>Save profile</Button>
  </form>
}

export function AddressesPage() { return <AccountGate title="Your addresses">{(owner) => <AddressManager key={owner} />}</AccountGate> }
function AddressManager() {
  const resource = useOrderRead('/me/addresses', true, validateAddresses)
  const write = useAccountWrite()
  const [editing, setEditing] = useState<Address | 'new' | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const disabled = write.busy || write.blocked || resource.loading || !resource.data
  function refresh() { setEditing(null); setDeleting(null); resource.retry() }
  function save(draft: AddressDraft) {
    if (disabled || !editing) return
    const current = editing
    void write.run(async () => {
      const value = validateAddress(await request<Address>(`/me/addresses${current === 'new' ? '' : `/${current.id}`}`, {
        authenticated: true, method: current === 'new' ? 'POST' : 'PATCH', body: JSON.stringify(draft),
      }))
      if ((current !== 'new' && value.id !== current.id) || Object.entries(draft).some(([key, field]) => value[key as keyof Address] !== field)) throw new Error('The saved address could not be confirmed.')
      return value
    }, refresh, current === 'new' ? 'Address added.' : 'Address updated.')
  }
  return <>
    <p>Save up to ten delivery addresses. Changes do not alter existing orders. At checkout, explicitly choose an address to copy into your delivery details.</p>
    {resource.loading && <p role="status">Loading addresses…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <>
      {!resource.data.length && <p>You have no saved addresses.</p>}
      {resource.data.map((address) => <article className="account-card" key={address.id}>
        <h2>{address.label || 'Delivery address'}{address.is_default ? ' · Default' : ''}</h2>
        <p>{address.street}</p><p>{address.city}, {address.province}</p>
        <div className="option-row">
          <Button className="button-secondary" disabled={disabled} onClick={() => { setEditing(address); setDeleting(null) }}>Edit {address.label || 'address'}</Button>
          {!address.is_default && <Button className="button-secondary" disabled={disabled} onClick={() => void write.run(async () => {
            const value = validateAddress(await request<Address>(`/me/addresses/${address.id}/set-default`, { authenticated: true, method: 'POST' }))
            if (value.id !== address.id || !value.is_default) throw new Error('The default address could not be confirmed.')
            return value
          }, refresh, 'Default address updated.')}>Make {address.label || 'address'} default</Button>}
          <Button className="button-secondary" disabled={disabled} onClick={() => { setDeleting(address.id); setEditing(null) }}>Delete {address.label || 'address'}</Button>
        </div>
        {deleting === address.id && <div><p>Delete this saved address? Existing orders are unchanged. Deleting a default does not choose a replacement.</p>
          <Button disabled={disabled} onClick={() => void write.run(async () => {
            const result = await request<unknown>(`/me/addresses/${address.id}`, { authenticated: true, method: 'DELETE' })
            if (result !== undefined) throw new Error('Address deletion could not be confirmed.')
          }, refresh, 'Address deleted.')}>Yes, delete address</Button>{' '}
          <Button className="button-secondary" disabled={write.busy} onClick={() => setDeleting(null)}>Keep address</Button>
        </div>}
      </article>)}
      {resource.data.length >= 10 ? <p>You have reached the ten-address limit.</p> : <Button disabled={disabled} onClick={() => { setEditing('new'); setDeleting(null) }}>Add address</Button>}
      {editing && <AddressForm key={editing === 'new' ? 'new' : editing.id} initial={editing === 'new' ? null : editing} disabled={Boolean(disabled)} save={save} cancel={() => setEditing(null)} />}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={refresh}>Refresh addresses</Button>
  </>
}
function AddressForm({ initial, disabled, save, cancel }: { initial: Address | null; disabled: boolean; save: (value: AddressDraft) => void; cancel: () => void }) {
  const [draft, setDraft] = useState<AddressDraft>(initial ?? { label: '', street: '', city: '', province: '', is_default: false })
  const [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (disabled) return; try { const value = addressPayload(draft); setError(null); save(value) } catch (reason) { setError(reason) } }}>
    <h2>{initial ? 'Edit delivery address' : 'New delivery address'}</h2>
    <Field label="Address label" value={draft.label ?? ''} maxLength={50} disabled={disabled} onChange={(e) => setDraft({ ...draft, label: e.target.value })} hint="Optional, such as Home or Office." />
    <Field label="Street address" value={draft.street} required minLength={10} maxLength={500} autoComplete="street-address" disabled={disabled} onChange={(e) => setDraft({ ...draft, street: e.target.value })} />
    <Field label="City" value={draft.city} required minLength={2} maxLength={100} autoComplete="address-level2" disabled={disabled} onChange={(e) => setDraft({ ...draft, city: e.target.value })} />
    <Field label="Province" value={draft.province} required minLength={2} maxLength={100} autoComplete="address-level1" disabled={disabled} onChange={(e) => setDraft({ ...draft, province: e.target.value })} />
    <label className="checkbox-label"><input type="checkbox" checked={draft.is_default} disabled={disabled} onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })} />Use as default address</label>
    {Boolean(error) && <ErrorNotice error={error} />}
    <Button type="submit" disabled={disabled}>Save address</Button><Button className="button-secondary" disabled={disabled} onClick={cancel}>Discard address draft</Button>
  </form>
}
