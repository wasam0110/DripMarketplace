import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { SellerStatus } from '../seller/SellerStatus'

export function PortalPage({ role }: { role: 'seller' | 'admin' }) {
  const { user, loading, error } = useAuth()
  const title = role === 'seller' ? 'Seller workspace' : 'Admin workspace'
  if (loading) return <section className="container page" aria-busy="true">
    <h1>Checking your session</h1><p role="status">Restoring your account before opening this workspace.</p>
  </section>
  if (error) return <section className="container page">
    <h1>Session could not be restored</h1><p role="alert">{error}</p>
    <Link className="button" to="/login">Return to sign in</Link>
  </section>
  if (!user) return <section className="container page">
    <h1>Sign in to your workspace</h1><p>A {role} account is required to open this page.</p>
    <Link className="button" to="/login">Sign in</Link>
  </section>
  // This UI boundary is not API authorization; every future data request needs server checks.
  if (user.role !== role) return <section className="container page">
    <h1>This workspace is not available to your account</h1>
    <p>You are signed in, but this page requires a different account role.</p>
    <Link className="button" to={accountDestination(user.role)}>Return to your workspace</Link>
    <p><Link to="/account">Manage your account or sign out</Link></p>
  </section>
  return <section className="container page account-page">
    <p className="eyebrow">WearHowZ · {role === 'seller' ? 'For independent labels' : 'Platform management'}</p>
    <h1>{title}</h1>
    <p className="lead">Welcome{user.first_name ? `, ${user.first_name}` : ''}. Your account has a dedicated place to start.</p>
    <div className="account-card">
      <h2>Your account</h2>
      <dl><dt>Email</dt><dd>{user.email}</dd><dt>Email status</dt><dd>{user.has_verified_email ? 'Verified' : 'Verification needed'}</dd></dl>
      <p><Link className="text-link" to="/account">Account settings and sign out</Link></p>
      <p><Link className="text-link" to="/">Visit the storefront</Link></p>
    </div>
    {role === 'seller' && <SellerStatus key={user.id} verified={user.has_verified_email} />}
    {role === 'admin' && <div className="account-card"><h2>Seller applications</h2>{user.has_verified_email
      ? <Link className="text-link" to="/admin/sellers">Review seller applications</Link>
      : <p>Verify your email before reviewing seller applications.</p>}</div>}
    <div className="account-card">
      <h2>{role === 'seller' ? 'Your selling tools are next' : 'More management tools'}</h2>
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/products">Moderate products</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/reviews">Moderate customer reviews</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/content">Manage banners</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/orders">Inspect orders</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/cod">Review COD queue</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/payments">Inspect payments and COD collection</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/refunds">Inspect refunds and recorded transfers</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/payouts">Review seller payouts and transfer records</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/settings">Manage platform settings</Link></p>}
      {role === 'admin' && user.has_verified_email && <p><Link className="text-link" to="/admin/returns">Review returns</Link> · <Link className="text-link" to="/admin/disputes">Review disputes</Link></p>}
      <p>{role === 'seller'
        ? 'Catalogue, fulfilment and wallet tools are not connected in this frontend checkpoint. Your application status above comes from the server; your account role alone does not confirm that your brand is approved to sell.'
        : 'Seller reviews, registration-payment records, product moderation and customer review moderation are connected. Banner management, orders, COD decisions and collection, refunds, returns, disputes, seller payout records and platform settings are also connected. PayFast reconciliation follows separately.'}</p>
      <p className="muted">No operational totals or actions are shown on this workspace overview. Open the connected tools to inspect current records.</p>
    </div>
  </section>
}
