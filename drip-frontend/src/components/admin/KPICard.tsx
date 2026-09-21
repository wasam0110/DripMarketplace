import type { ReactNode } from 'react'

interface Props { label: string; value: string | number; delta?: string; icon?: ReactNode; accent?: boolean }

export function KPICard({ label, value, delta, icon, accent }: Props) {
  return (
    <div className={`panel flex flex-col gap-2 ${accent ? 'border-accent/30 bg-accent/5' : ''}`}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold tracking-widest text-muted uppercase">{label}</p>
        {icon && <span className="text-muted">{icon}</span>}
      </div>
      <p className={`text-2xl font-bold ${accent ? 'text-accent' : 'text-white'}`}>{value}</p>
      {delta && <p className="text-xs text-muted">{delta}</p>}
    </div>
  )
}
