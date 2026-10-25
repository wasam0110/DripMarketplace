import { Link, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import { Layout } from './components/Layout'
import { ErrorBoundary, NotFound } from './components/ui'
import { AccountPage, AuthPage, VerifyEmailPage } from './pages/AuthPages'
import { BrandPage, BrandsPageView, CataloguePageView, HomePage } from './pages/Storefront'
import { ProductPage } from './pages/ProductPage'
import { BagPage } from './pages/BagPage'
import { CartProvider } from './cart/CartProvider'
import { CheckoutPage } from './pages/CheckoutPage'
import { GuestTrackingPage, OrderDetailPage, OrdersPage } from './pages/OrderPages'
import { OrderAccessProvider } from './orders/access'
import { SavedProvider } from './saved/SavedProvider'
import { SavedPage } from './pages/SavedPage'
import { MyReviewsPage } from './reviews/MyReviewsPage'
import { AddressesPage, ProfilePage } from './account/AccountDetails'
import { NotificationPreferencesPage } from './account/NotificationPreferencesPage'
import { NotificationInboxPage } from './account/NotificationInboxPage'
import { ChangePasswordPage } from './account/ChangePasswordPage'
import { AvatarPage } from './account/AvatarPage'
import { GuestReturnPage, ReturnDetailPage, ReturnsPage } from './pages/ReturnPages'
import { DisputePage } from './pages/DisputePage'
import { ReviewPhotosPage } from './reviews/ReviewPhotosPage'
import { DeleteAccountPage } from './account/DeleteAccountPage'
import { GoogleCallbackPage } from './auth/GoogleCallbackPage'
import { PaymentStatusPage } from './payments/PaymentStatusPage'

export default function App() {
  return <ErrorBoundary><AuthProvider><OrderAccessProvider><CartProvider><SavedProvider><Routes>
    <Route element={<Layout />}>
      <Route index element={<HomePage />} />
      <Route path="clothing" element={<CataloguePageView />} />
      <Route path="brands" element={<BrandsPageView />} />
      <Route path="brands/:slug" element={<BrandPage />} />
      <Route path="products/:id" element={<ProductPage />} />
      <Route path="bag" element={<BagPage />} />
      <Route path="saved" element={<SavedPage />} />
      <Route path="checkout" element={<CheckoutPage />} />
      <Route path="payments/:id" element={<PaymentStatusPage />} />
      <Route path="order/success/:id" element={<PaymentStatusPage />} />
      <Route path="orders" element={<OrdersPage />} />
      <Route path="orders/:id" element={<OrderDetailPage />} />
      <Route path="track" element={<GuestTrackingPage />} />
      <Route path="returns" element={<ReturnsPage />} />
      <Route path="returns/:id" element={<ReturnDetailPage />} />
      <Route path="returns/:id/dispute" element={<DisputePage />} />
      <Route path="track-return" element={<GuestReturnPage />} />
      <Route path="login" element={<AuthPage key="login" mode="login" />} />
      <Route path="register" element={<AuthPage key="register" mode="register" />} />
      <Route path="forgot-password" element={<AuthPage key="forgot" mode="forgot" />} />
      <Route path="reset-password" element={<AuthPage key="reset" mode="reset" />} />
      <Route path="account" element={<AccountPage />} />
      <Route path="account/reviews" element={<MyReviewsPage />} />
      <Route path="account/reviews/:id/photos" element={<ReviewPhotosPage />} />
      <Route path="account/profile" element={<ProfilePage />} />
      <Route path="account/addresses" element={<AddressesPage />} />
      <Route path="account/notifications" element={<NotificationPreferencesPage />} />
      <Route path="account/inbox" element={<NotificationInboxPage />} />
      <Route path="account/password" element={<ChangePasswordPage />} />
      <Route path="account/photo" element={<AvatarPage />} />
      <Route path="account/delete" element={<DeleteAccountPage />} />
      <Route path="verify-email" element={<VerifyEmailPage />} />
      <Route path="auth/verify-email" element={<VerifyEmailPage />} />
      <Route path="auth/callback" element={<GoogleCallbackPage />} />
      <Route path="help" element={<section className="container page help-page">
        <p className="eyebrow">WearHowZ help</p><h1>A little help,<br /><em>when you need it.</em></h1>
        <details open><summary>Shopping across brands</summary><p>Your bag can contain pieces from several labels. Each brand fulfils its own items, so shipments can have different statuses.</p></details>
        <details><summary>Returns</summary><p>Return conditions belong to the individual brand. Review the policy on the brand page before ordering.</p><p><Link to="/returns">Account return history</Link> or <Link to="/track-return">track a guest return</Link>.</p></details>
        <details><summary>Track an order</summary><p><Link to="/orders">Account order history</Link> or <Link to="/track">secure guest tracking</Link>. Each brand can ship separately.</p></details>
        <details><summary>About this build</summary><p>Browsing, email sign-in, COD checkout with saved-address selection, order tracking, profile editing and saved-address management are connected. Device saves and the account wishlist remain separate. Online payments, remaining account settings and portals are still being built.</p></details>
      </section>} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes></SavedProvider></CartProvider></OrderAccessProvider></AuthProvider></ErrorBoundary>
}
