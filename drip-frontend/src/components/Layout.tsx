import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { useCart } from '../cart/CartProvider'
import { Arrow, Icon } from './ui'
import { SavedFeedback } from '../saved/SavedProvider'

export function Layout() {
  const { user } = useAuth()
  const { count } = useCart()
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const searchInput = useRef<HTMLInputElement>(null)
  const searchButton = useRef<HTMLButtonElement>(null)
  const main = useRef<HTMLElement>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const initialRender = useRef(true)

  useEffect(() => {
    setMenuOpen(false)
    setSearchOpen(false)
    if (initialRender.current) { initialRender.current = false; return }
    main.current?.focus()
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [location.pathname, location.search])

  useEffect(() => { if (searchOpen) searchInput.current?.focus() }, [searchOpen])

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = String(new FormData(event.currentTarget).get('q') ?? '').trim()
    navigate(query ? `/clothing?q=${encodeURIComponent(query)}` : '/clothing')
  }

  return <div className="site-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <div className="announcement"><span>Independent labels. Distinct points of view.</span><span>Made for your point of view.</span></div>
    <header className="site-header">
      <div className="header-inner container">
        <Link className="logo" to="/" aria-label="WearHowZ home"><img src="/assets/wearhowz-logo.png" alt="WearHowZ" width="200" height="67" /></Link>
        <nav aria-label="Main navigation" className="desktop-nav">
          <NavLink to="/clothing?sort=newest">New arrivals</NavLink>
          <NavLink to="/clothing">Clothing</NavLink>
          <NavLink to="/brands">Brands</NavLink>
          <NavLink to="/saved">Saved pieces</NavLink>
        </nav>
        <div className="header-actions">
          <Link className="icon-button bag-link" to="/bag" aria-label={`Bag, ${count} items`}><Icon name="bag" />{count > 0 && <span className="bag-count">{count}</span>}</Link>
          <button ref={searchButton} className="icon-button" aria-label={searchOpen ? 'Close search' : 'Search clothing'}
            aria-expanded={searchOpen} aria-controls="site-search" onClick={() => setSearchOpen(!searchOpen)}><Icon name="search" /></button>
          <Link className="account-link" aria-label={user ? 'My account' : 'Account'} to={user ? '/account' : '/login'}><Icon name="account" /><span>{user ? 'My account' : 'Account'}</span></Link>
          <button ref={menuButton} className="icon-button menu-toggle" aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen} aria-controls="mobile-nav" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} /></button>
        </div>
      </div>
      {menuOpen && <nav id="mobile-nav" className="mobile-nav container" aria-label="Mobile navigation"
        onKeyDown={(event) => { if (event.key === 'Escape') { setMenuOpen(false); menuButton.current?.focus() } }}>
        <Link to="/clothing?sort=newest">New arrivals <Arrow /></Link>
        <Link to="/clothing">Clothing <Arrow /></Link>
        <Link to="/brands">Brands <Arrow /></Link>
        <Link to="/saved">Saved pieces <Arrow /></Link>
        <Link to={user ? '/account' : '/login'}>Your account <Arrow /></Link>
      </nav>}
      {searchOpen && <form id="site-search" className="search-panel container" onSubmit={search}
        onKeyDown={(event) => { if (event.key === 'Escape') { setSearchOpen(false); searchButton.current?.focus() } }}>
        <label className="sr-only" htmlFor="header-search">Search clothing</label>
        <input ref={searchInput} id="header-search" name="q" maxLength={200} type="search" placeholder="Find your next piece…" />
        <button className="button" type="submit">Search <Arrow /></button>
      </form>}
    </header>
    <main ref={main} id="main" tabIndex={-1}><SavedFeedback /><Outlet /></main>
    <footer className="site-footer container">
      <div><Link to="/" className="footer-wordmark">WearHowZ</Link><p>Independent style, all in one place.</p></div>
      <nav aria-label="Footer"><Link to="/help">Help & returns</Link><Link to="/track">Track a guest order</Link><Link to="/saved">Saved pieces</Link><Link to="/account">Your account</Link><Link to="/brands">Discover the labels <Arrow /></Link></nav>
      <small>© {new Date().getFullYear()} WearHowZ</small>
    </footer>
  </div>
}
