import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8">
        <div className="col-span-2 sm:col-span-1">
          <span className="font-mono font-bold text-xl">DRIP<span className="text-accent">.</span></span>
          <p className="text-muted text-xs mt-2 max-w-[180px]">Independent fashion, curated in one place.</p>
        </div>
        {[
          { heading: 'Shop',    links: [['All products', '/shop'], ['New arrivals', '/shop?sort=newest'], ['Sale', '/shop?on_sale=true']] },
          { heading: 'Sell',    links: [['Become a seller', '/sell'], ['Seller login', '/login'], ['Commission rates', '/sell#rates']] },
          { heading: 'Support', links: [['Track order', '/track'], ['Returns', '/returns'], ['Contact', '/contact']] },
        ].map(col => (
          <div key={col.heading}>
            <p className="text-[10px] font-bold tracking-widest text-muted mb-3 uppercase">{col.heading}</p>
            <ul className="flex flex-col gap-2">
              {col.links.map(([label, to]) => (
                <li key={label}><Link to={to} className="text-xs text-muted hover:text-white transition-colors">{label}</Link></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row justify-between gap-2">
          <p className="text-[10px] text-muted">© 2026 DRIP Marketplace. All rights reserved.</p>
          <p className="text-[10px] text-muted">Built in Pakistan.</p>
        </div>
      </div>
    </footer>
  )
}
