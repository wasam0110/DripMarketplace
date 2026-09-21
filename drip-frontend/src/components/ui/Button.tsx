import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'ghost' | 'danger'
  size?:    'sm' | 'md' | 'lg'
  loading?: boolean
  icon?:    ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, children, className = '', disabled, ...rest }, ref) => {
    const base = 'inline-flex items-center justify-center gap-2 font-bold tracking-wide transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed'
    const variants = {
      primary: 'bg-accent text-bg hover:opacity-90 active:opacity-75',
      outline: 'border border-border text-white hover:border-accent hover:text-accent',
      ghost:   'text-muted hover:text-white',
      danger:  'bg-danger text-white hover:opacity-90',
    }
    const sizes = { sm: 'text-xs px-4 py-2', md: 'text-sm px-6 py-3', lg: 'text-base px-8 py-4' }
    return (
      <button ref={ref} disabled={disabled || loading} className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...rest}>
        {loading ? <Loader2 size={15} className="animate-spin" /> : icon}
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
