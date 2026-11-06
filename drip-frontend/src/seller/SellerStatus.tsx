import { Link } from 'react-router'
import { ApiError } from '../api/client'
import { Button, ErrorNotice } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'

export interface SellerSummary {
  id: string
  brand_name: string
  status: string
  registration_amount_due: string
  registration_paid_at: string | null
}

/** Read only displayed fields; unknown states never imply approval. */
export function validateSellerSummary(value: SellerSummary): SellerSummary {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id)
    || typeof value.brand_name !== 'string' || !value.brand_name.trim()
    || typeof value.status !== 'string' || !value.status.trim()
    || typeof value.registration_amount_due !== 'string'
    || !/^\d{1,8}(\.\d{1,2})?$/.test(value.registration_amount_due)
    || !(value.registration_paid_at === null || (typeof value.registration_paid_at === 'string'
      && /^\d{4}-\d{2}-\d{2}T/.test(value.registration_paid_at) && Number.isFinite(Date.parse(value.registration_paid_at))))
    || (value.registration_paid_at !== null && Number(value.registration_amount_due) !== 0)) {
    throw new Error('The server returned incomplete seller status. Refresh to try again.')
  }
  return { id: value.id, brand_name: value.brand_name, status: value.status,
    registration_amount_due: value.registration_amount_due, registration_paid_at: value.registration_paid_at }
}

const states: Record<string, { title: string; detail: string }> = {
  pending_payment: { title: 'Registration payment pending', detail: 'Your registration payment has not been confirmed. Contact WearHowZ support for verified transfer instructions or to check an existing transfer. This page cannot take payment or confirm a receipt.' },
  pending_approval: { title: 'Application awaiting approval', detail: 'Your application is awaiting review. Payment confirmation alone does not approve a brand. No review date is available from the server.' },
  active: { title: 'Brand approved', detail: 'Your brand is active. Manage your shop and earnings below.' },
  suspended: { title: 'Selling access suspended', detail: 'Your brand is suspended. Contact WearHowZ support for guidance; refreshing this page does not restore access.' },
  rejected: { title: 'Application not approved', detail: 'Your application was rejected. The profile API does not provide a reason or reapplication instructions. Contact WearHowZ support before submitting another application.' },
}

export function SellerStatus({ verified }: { verified: boolean }) {
  if (!verified) return <div className="account-card">
    <h2>Verify your email first</h2>
    <p>Your seller status can be checked after email verification. Use the verification link sent to your email; signing in with a seller role does not confirm brand approval.</p>
    <Link className="text-link" to="/account">Manage your account</Link>
  </div>
  return <SellerStatusRead />
}

function SellerStatusRead() {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  const profile = resource.data
  const state = profile && Object.hasOwn(states, profile.status) ? states[profile.status] : null
  return <div className="account-card" aria-busy={resource.loading}>
    <h2>Your brand application</h2>
    {resource.loading && <p role="status">Loading seller status…</p>}
    {Boolean(resource.error) && <>
      <ErrorNotice error={resource.error} />
      <p>{resource.error instanceof ApiError && [403, 404].includes(resource.error.status)
        ? 'Seller details are unavailable to this session. Check your verified account or contact support; this does not establish an application decision.'
        : 'Your latest application state could not be confirmed. No approval or payment status is assumed.'}</p>
    </>}
    {profile && <>
      <h3>{profile.brand_name}</h3>
      <p><Link className="text-link" to="/seller/profile">Edit brand profile</Link></p>
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/products">View seller catalogue</Link></p>}
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/inventory">Manage seller inventory</Link></p>}
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/orders">Manage seller orders</Link></p>}
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/returns">Manage seller returns</Link></p>}
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/wallet">View wallet and payouts</Link></p>}
      {profile.status === 'active' && <p><Link className="text-link" to="/seller/analytics">View analytics and commission</Link></p>}
      <p role="status"><strong>{state?.title ?? 'Application status unavailable'}</strong></p>
      <p>{state?.detail ?? 'The server returned an unrecognized application state. Contact support; no selling permission is inferred.'}</p>
      <dl>
        <dt>Registration amount outstanding</dt>
        <dd>{new Intl.NumberFormat('en-PK', { style: 'currency', currency: 'PKR' }).format(Number(profile.registration_amount_due))}</dd>
        <dt>Registration payment confirmation</dt>
        <dd>{profile.registration_paid_at ? `Recorded on ${orderDate(profile.registration_paid_at)}`
          : Number(profile.registration_amount_due) === 0 ? 'No payment due; no paid receipt recorded.' : 'Not recorded.'}</dd>
      </dl>
      <p className="muted">These are the latest fetched server records, not a receipt upload or a live status feed. No bank details, approval reason or payment action is supplied here.</p>
    </>}
    <Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh seller status</Button>
  </div>
}
