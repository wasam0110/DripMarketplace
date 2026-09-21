export function CODVerification({ orderNumber }: { orderNumber: string }) {
  return (
    <div className="flex flex-col gap-4 p-6 border border-warning/30 bg-warning/5">
      <p className="text-warning text-xs font-bold tracking-widest uppercase">COD order placed</p>
      <p className="text-sm text-muted">
        Order <span className="text-white font-mono">{orderNumber}</span> is pending verification.
        Our team will call you on the number provided within 24 hours to confirm.
      </p>
      <p className="text-xs text-muted">Keep your phone handy. Unconfirmed orders are cancelled after 24 hours.</p>
    </div>
  )
}
