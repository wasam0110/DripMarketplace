import { Link } from 'react-router-dom'

interface Props { used: number; total: number }

export function SlotMeter({ used, total }: Props) {
  const pct = Math.min(100, Math.round((used / total) * 100))
  const isNearFull = pct >= 80
  return (
    <div className="panel flex flex-col gap-3">
      <div className="flex justify-between items-baseline">
        <p className="text-xs font-bold tracking-widest text-muted uppercase">Slot meter</p>
        <span className={`text-xs font-mono ${isNearFull ? 'text-warning' : 'text-muted'}`}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-border w-full">
        <div className={`h-full transition-all ${isNearFull ? 'bg-warning' : 'bg-accent'}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted"><span className="text-white font-bold">{used}</span> published / <span className="text-white font-bold">{total}</span> slots</p>
      {isNearFull && (
        <Link to="/dashboard/settings?tab=slots" className="text-xs text-accent hover:underline">
          Buy more slots →
        </Link>
      )}
    </div>
  )
}
