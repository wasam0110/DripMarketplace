import { lazy, Suspense } from 'react'
import { Link, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import { Layout } from './components/Layout'
import { ErrorBoundary, NotFound } from './components/ui'
import { CartProvider } from './cart/CartProvider'
import { OrderAccessProvider } from './orders/access'
import { SavedProvider } from './saved/SavedProvider'

const AccountPage = lazy(() => import('./pages/AuthPages').then(({ AccountPage }) => ({ default: AccountPage })))
const AuthPage = lazy(() => import('./pages/AuthPages').then(({ AuthPage }) => ({ default: AuthPage })))
const VerifyEmailPage = lazy(() => import('./pages/AuthPages').then(({ VerifyEmailPage }) => ({ default: VerifyEmailPage })))
const BrandPage = lazy(() => import('./pages/Storefront').then(({ BrandPage }) => ({ default: BrandPage })))
const BrandsPageView = lazy(() => import('./pages/Storefront').then(({ BrandsPageView }) => ({ default: BrandsPageView })))
const CataloguePageView = lazy(() => import('./pages/Storefront').then(({ CataloguePageView }) => ({ default: CataloguePageView })))
const HomePage = lazy(() => import('./pages/Storefront').then(({ HomePage }) => ({ default: HomePage })))
const ProductPage = lazy(() => import('./pages/ProductPage').then(({ ProductPage }) => ({ default: ProductPage })))
const BagPage = lazy(() => import('./pages/BagPage').then(({ BagPage }) => ({ default: BagPage })))
const CheckoutPage = lazy(() => import('./pages/CheckoutPage').then(({ CheckoutPage }) => ({ default: CheckoutPage })))
const GuestTrackingPage = lazy(() => import('./pages/OrderPages').then(({ GuestTrackingPage }) => ({ default: GuestTrackingPage })))
const OrderDetailPage = lazy(() => import('./pages/OrderPages').then(({ OrderDetailPage }) => ({ default: OrderDetailPage })))
const OrdersPage = lazy(() => import('./pages/OrderPages').then(({ OrdersPage }) => ({ default: OrdersPage })))
const SavedPage = lazy(() => import('./pages/SavedPage').then(({ SavedPage }) => ({ default: SavedPage })))
const MyReviewsPage = lazy(() => import('./reviews/MyReviewsPage').then(({ MyReviewsPage }) => ({ default: MyReviewsPage })))
const AddressesPage = lazy(() => import('./account/AccountDetails').then(({ AddressesPage }) => ({ default: AddressesPage })))
const ProfilePage = lazy(() => import('./account/AccountDetails').then(({ ProfilePage }) => ({ default: ProfilePage })))
const NotificationPreferencesPage = lazy(() => import('./account/NotificationPreferencesPage').then(({ NotificationPreferencesPage }) => ({ default: NotificationPreferencesPage })))
const NotificationInboxPage = lazy(() => import('./account/NotificationInboxPage').then(({ NotificationInboxPage }) => ({ default: NotificationInboxPage })))
const ChangePasswordPage = lazy(() => import('./account/ChangePasswordPage').then(({ ChangePasswordPage }) => ({ default: ChangePasswordPage })))
const AvatarPage = lazy(() => import('./account/AvatarPage').then(({ AvatarPage }) => ({ default: AvatarPage })))
const GuestReturnPage = lazy(() => import('./pages/ReturnPages').then(({ GuestReturnPage }) => ({ default: GuestReturnPage })))
const ReturnDetailPage = lazy(() => import('./pages/ReturnPages').then(({ ReturnDetailPage }) => ({ default: ReturnDetailPage })))
const ReturnsPage = lazy(() => import('./pages/ReturnPages').then(({ ReturnsPage }) => ({ default: ReturnsPage })))
const DisputePage = lazy(() => import('./pages/DisputePage').then(({ DisputePage }) => ({ default: DisputePage })))
const ReviewPhotosPage = lazy(() => import('./reviews/ReviewPhotosPage').then(({ ReviewPhotosPage }) => ({ default: ReviewPhotosPage })))
const DeleteAccountPage = lazy(() => import('./account/DeleteAccountPage').then(({ DeleteAccountPage }) => ({ default: DeleteAccountPage })))
const GoogleCallbackPage = lazy(() => import('./auth/GoogleCallbackPage').then(({ GoogleCallbackPage }) => ({ default: GoogleCallbackPage })))
const PaymentStatusPage = lazy(() => import('./payments/PaymentStatusPage').then(({ PaymentStatusPage }) => ({ default: PaymentStatusPage })))
const PortalPage = lazy(() => import('./pages/PortalPage').then(({ PortalPage }) => ({ default: PortalPage })))
const SellerRegistrationPage = lazy(() => import('./seller/SellerRegistrationPage').then(({ SellerRegistrationPage }) => ({ default: SellerRegistrationPage })))
const SellerProfilePage = lazy(() => import('./seller/SellerProfilePage').then(({ SellerProfilePage }) => ({ default: SellerProfilePage })))
const SellerLogoPage = lazy(() => import('./seller/SellerLogoPage').then(({ SellerLogoPage }) => ({ default: SellerLogoPage })))
const SellerCataloguePage = lazy(() => import('./seller/SellerCataloguePage').then(({ SellerCataloguePage }) => ({ default: SellerCataloguePage })))
const SellerProductEditorPage = lazy(() => import('./seller/SellerProductEditorPage').then(({ SellerProductEditorPage }) => ({ default: SellerProductEditorPage })))
const SellerInventoryPage = lazy(() => import('./seller/SellerInventoryPage').then(({ SellerInventoryPage }) => ({ default: SellerInventoryPage })))
const SellerFulfilmentPage = lazy(() => import('./seller/SellerFulfilmentPage').then(({ SellerFulfilmentPage }) => ({ default: SellerFulfilmentPage })))
const SellerReturnsPage = lazy(() => import('./seller/SellerReturnsPage').then(({ SellerReturnsPage }) => ({ default: SellerReturnsPage })))
const SellerWalletPage = lazy(() => import('./seller/SellerWalletPage').then(({ SellerWalletPage }) => ({ default: SellerWalletPage })))
const SellerAnalyticsPage = lazy(() => import('./seller/SellerAnalyticsPage').then(({ SellerAnalyticsPage }) => ({ default: SellerAnalyticsPage })))
const AdminSellersPage = lazy(() => import('./admin/AdminSellersPage').then(({ AdminSellersPage }) => ({ default: AdminSellersPage })))
const AdminProductsPage = lazy(() => import('./admin/AdminProductsPage').then(({ AdminProductsPage }) => ({ default: AdminProductsPage })))
const AdminReviewsPage = lazy(() => import('./admin/AdminReviewsPage').then(({ AdminReviewsPage }) => ({ default: AdminReviewsPage })))
const AdminContentPage = lazy(() => import('./admin/AdminContentPage').then(({ AdminContentPage }) => ({ default: AdminContentPage })))
const AdminOrdersPage = lazy(() => import('./admin/AdminOrdersPage').then(({ AdminOrdersPage }) => ({ default: AdminOrdersPage })))
const AdminCODPage = lazy(() => import('./admin/AdminCODPage').then(({ AdminCODPage }) => ({ default: AdminCODPage })))
const AdminPaymentsPage = lazy(() => import('./admin/AdminPaymentsPage').then(({ AdminPaymentsPage }) => ({ default: AdminPaymentsPage })))
const AdminRefundsPage = lazy(() => import('./admin/AdminRefundsPage').then(({ AdminRefundsPage }) => ({ default: AdminRefundsPage })))
const AdminReturnsPage = lazy(() => import('./admin/AdminReturnsPage').then(({ AdminReturnsPage }) => ({ default: AdminReturnsPage })))
const AdminPayoutsPage = lazy(() => import('./admin/AdminPayoutsPage').then(({ AdminPayoutsPage }) => ({ default: AdminPayoutsPage })))
const AdminSettingsPage = lazy(() => import('./admin/AdminSettingsPage').then(({ AdminSettingsPage }) => ({ default: AdminSettingsPage })))
const AdminAnalyticsPage = lazy(() => import('./admin/AdminAnalyticsPage').then(({ AdminAnalyticsPage }) => ({ default: AdminAnalyticsPage })))
const AdminNotificationsPage = lazy(() => import('./admin/AdminNotificationsPage').then(({ AdminNotificationsPage }) => ({ default: AdminNotificationsPage })))
const AdminTwoFactorPage = lazy(() => import('./admin/AdminTwoFactorPage').then(({ AdminTwoFactorPage }) => ({ default: AdminTwoFactorPage })))

export default function App() {
  return <ErrorBoundary><AuthProvider><OrderAccessProvider><CartProvider><SavedProvider><Suspense fallback={<p className="container page" role="status">Loading page…</p>}><Routes>
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
      <Route path="admin/analytics" element={<AdminAnalyticsPage />} />
      <Route path="admin/notifications" element={<AdminNotificationsPage />} />
      <Route path="admin/security/2fa" element={<AdminTwoFactorPage />} />
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
  </Routes></Suspense></SavedProvider></CartProvider></OrderAccessProvider></AuthProvider></ErrorBoundary>
}
