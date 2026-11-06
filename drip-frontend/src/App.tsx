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
import { PortalPage } from './pages/PortalPage'
import { SellerRegistrationPage } from './seller/SellerRegistrationPage'
import { SellerProfilePage } from './seller/SellerProfilePage'
import { SellerLogoPage } from './seller/SellerLogoPage'
import { SellerCataloguePage } from './seller/SellerCataloguePage'
import { SellerProductEditorPage } from './seller/SellerProductEditorPage'
import { SellerInventoryPage } from './seller/SellerInventoryPage'
import { SellerFulfilmentPage } from './seller/SellerFulfilmentPage'
import { SellerReturnsPage } from './seller/SellerReturnsPage'
import { SellerWalletPage } from './seller/SellerWalletPage'
import { SellerAnalyticsPage } from './seller/SellerAnalyticsPage'
import { AdminSellersPage } from './admin/AdminSellersPage'
import { AdminProductsPage } from './admin/AdminProductsPage'
import { AdminReviewsPage } from './admin/AdminReviewsPage'
import { AdminContentPage } from './admin/AdminContentPage'
import { AdminOrdersPage } from './admin/AdminOrdersPage'
import { AdminCODPage } from './admin/AdminCODPage'
import { AdminPaymentsPage } from './admin/AdminPaymentsPage'
import { AdminRefundsPage } from './admin/AdminRefundsPage'
import { AdminReturnsPage } from './admin/AdminReturnsPage'
import { AdminPayoutsPage } from './admin/AdminPayoutsPage'
import { AdminSettingsPage } from './admin/AdminSettingsPage'

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
      <Route path="seller" element={<PortalPage role="seller" />} />
      <Route path="seller/register" element={<SellerRegistrationPage />} />
      <Route path="seller/profile" element={<SellerProfilePage />} />
      <Route path="seller/logo" element={<SellerLogoPage />} />
      <Route path="seller/products" element={<SellerCataloguePage />} />
      <Route path="seller/inventory" element={<SellerInventoryPage />} />
      <Route path="seller/orders" element={<SellerFulfilmentPage />} />
      <Route path="seller/orders/:id" element={<SellerFulfilmentPage detail />} />
      <Route path="seller/returns" element={<SellerReturnsPage />} />
      <Route path="seller/returns/:id" element={<SellerReturnsPage detail />} />
      <Route path="seller/wallet" element={<SellerWalletPage />} />
      <Route path="seller/analytics" element={<SellerAnalyticsPage />} />
      <Route path="seller/wallet/accounts" element={<SellerWalletPage accountsOnly />} />
      <Route path="seller/products/new" element={<SellerProductEditorPage create />} />
      <Route path="seller/products/:id/edit" element={<SellerProductEditorPage />} />
      <Route path="seller/products/:id/options" element={<SellerProductEditorPage options />} />
      <Route path="seller/products/:id/media" element={<SellerProductEditorPage media />} />
      <Route path="admin" element={<PortalPage role="admin" />} />
      <Route path="admin/sellers" element={<AdminSellersPage />} />
      <Route path="admin/sellers/:id" element={<AdminSellersPage detail />} />
      <Route path="admin/products" element={<AdminProductsPage />} />
      <Route path="admin/products/:id" element={<AdminProductsPage detail />} />
      <Route path="admin/reviews" element={<AdminReviewsPage />} />
      <Route path="admin/reviews/:id" element={<AdminReviewsPage detail />} />
      <Route path="admin/content" element={<AdminContentPage />} />
      <Route path="admin/content/banners/new" element={<AdminContentPage create />} />
      <Route path="admin/content/banners/:id" element={<AdminContentPage detail />} />
      <Route path="admin/orders" element={<AdminOrdersPage />} />
      <Route path="admin/orders/:id" element={<AdminOrdersPage detail />} />
      <Route path="admin/cod" element={<AdminCODPage />} />
      <Route path="admin/cod/:id" element={<AdminCODPage detail />} />
      <Route path="admin/payments" element={<AdminPaymentsPage />} />
      <Route path="admin/payments/:id" element={<AdminPaymentsPage detail />} />
      <Route path="admin/payments/:id/refunds" element={<AdminRefundsPage mode="payment" />} />
      <Route path="admin/refunds" element={<AdminRefundsPage />} />
      <Route path="admin/refunds/:id" element={<AdminRefundsPage mode="detail" />} />
      <Route path="admin/returns" element={<AdminReturnsPage />} />
      <Route path="admin/payouts" element={<AdminPayoutsPage />} />
      <Route path="admin/settings" element={<AdminSettingsPage />} />
      <Route path="admin/payouts/:id" element={<AdminPayoutsPage detail />} />
      <Route path="admin/returns/:id" element={<AdminReturnsPage detail />} />
      <Route path="admin/disputes" element={<AdminReturnsPage disputes />} />
      <Route path="admin/disputes/:id" element={<AdminReturnsPage disputes detail />} />
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
