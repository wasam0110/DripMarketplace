interface BadgeProps {
  label: string
  variant?: 'accent' | 'danger' | 'success' | 'warning' | 'muted'
  className?: string
}
const styles = {
  accent:  'bg-accent text-bg',
  danger:  'bg-danger/20 text-danger border border-danger/30',
  success: 'bg-success/20 text-success border border-success/30',
  warning: 'bg-warning/20 text-warning border border-warning/30',
  muted:   'bg-border text-muted',
}
export function Badge({ label, variant = 'muted', className = '' }: BadgeProps) {
  return (
    <span className={`text-[10px] font-bold tracking-widest px-2 py-0.5 ${styles[variant]} ${className}`}>
      {label}
    </span>
  )
}
