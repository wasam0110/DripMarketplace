import { useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { request } from '../api/client'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { brandChanges, brandDraft, confirmBrandUpdate, profileLimits, validateBrandProfile, type BrandDraft, type BrandProfile } from './profile'

export function SellerProfilePage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Your brand profile</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage your brand</h1>
    {error && <ErrorNotice error={new Error(error)} />}<Link className="button" to="/login">Sign in</Link>
  </section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1>
    <Link className="button" to={accountDestination(user.role)}>Return to your workspace</Link>
  </section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1>
    <p>Use your email verification link before managing your brand.</p><Link to="/account">Manage your account</Link>
  </section>
  return <section className="container page account-page">
    <Link className="text-link" to="/seller">Back to seller workspace</Link>
    <p className="eyebrow">WearHowZ · Your label</p><h1>Your brand profile</h1>
    <ProfileManager key={user.id} />
  </section>
}

function ProfileManager() {
  const resource = useOrderRead('/seller/me', true, validateBrandProfile)
  const write = useAccountWrite()
  return <>
    <p>Update your label’s description, return policy, contact details and brand colour. These changes do not approve a brand or alter registration payment status.</p>
    <p className="muted">Brand name cannot be changed here. Avoid editing this profile in multiple tabs; the API does not provide version-conflict protection.</p>
    <p><Link className="text-link" to="/seller/logo">Manage your brand logo</Link></p>
    {resource.loading && <p role="status">Loading brand profile…</p>}
    {Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {resource.data && <BrandForm initial={resource.data} disabled={write.busy || write.blocked} save={(changes) => {
      const initial = resource.data!
      void write.run(async () => confirmBrandUpdate(await request<BrandProfile>('/seller/me', {
        authenticated: true, method: 'PATCH', body: JSON.stringify(changes),
      }), initial, changes), () => resource.retry(), 'Brand profile saved.')
    }} />}
    <p className="muted">Refresh discards unsaved edits and reloads the server profile. Drafts are not stored on this device. After an uncertain save, refreshing only inspects the data; it does not retry or unlock writing on this page.</p>
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={resource.retry}>Refresh brand profile</Button>
  </>
}

function BrandForm({ initial, disabled, save }: { initial: BrandProfile; disabled: boolean; save: (changes: Partial<BrandDraft>) => void }) {
  const [draft, setDraft] = useState(() => brandDraft(initial))
  const [error, setError] = useState<unknown>(null)
  const baseline = brandDraft(initial)
  const changed = (Object.keys(baseline) as (keyof BrandDraft)[]).some((key) => draft[key] !== baseline[key])
  const update = (key: keyof BrandDraft, value: string) => { setDraft((current) => ({ ...current, [key]: value })); setError(null) }
  return <form className="account-card auth-form" onSubmit={(event) => {
    event.preventDefault(); if (disabled || !changed) return
    try { const changes = brandChanges(draft, initial); setError(null); if (Object.keys(changes).length) save(changes) } catch (reason) { setError(reason) }
  }}>
    <h2>{initial.brand_name}</h2>
    <p>Clearing a text field removes its saved text. Brand colour is required. Only changed fields are sent when you save.</p>
    <fieldset className="auth-form review-fields" disabled={disabled}>
      <legend>Editable brand details</legend>
      {(['description', 'return_policy'] as const).map((key) => <div className="field" key={key}>
        <label htmlFor={`brand-${key}`}>{key === 'description' ? 'Brand description' : 'Return policy'}</label>
        <textarea id={`brand-${key}`} rows={4} maxLength={profileLimits[key]} value={draft[key]} onChange={(event) => update(key, event.target.value)} />
      </div>)}
      <Field label="WhatsApp number" type="tel" maxLength={20} value={draft.whatsapp_number} onChange={(event) => update('whatsapp_number', event.target.value)} />
      <Field label="Instagram handle" maxLength={100} value={draft.instagram_handle} onChange={(event) => update('instagram_handle', event.target.value)} />
      <Field label="Brand colour" required pattern="#[0-9A-Fa-f]{6}" maxLength={7} value={draft.brand_color} onChange={(event) => update('brand_color', event.target.value)} hint="Six-digit hex colour, for example #203C32. This saves your brand setting; it does not change this workspace’s theme." />
    </fieldset>
    {Boolean(error) && <ErrorNotice error={error} />}
    <p role="status">{changed ? 'You have unsaved brand changes.' : 'Showing your saved brand details.'}</p>
    <Button type="submit" disabled={disabled || !changed}>Save brand profile</Button>
    <Button className="button-secondary" disabled={disabled || !changed} onClick={() => { setDraft(brandDraft(initial)); setError(null) }}>Discard brand changes</Button>
  </form>
}
