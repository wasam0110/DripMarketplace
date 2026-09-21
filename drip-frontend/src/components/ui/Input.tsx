import { forwardRef, type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?:  string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className = '', ...rest }, ref) => (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs text-muted font-medium uppercase tracking-widest">{label}</label>}
      <input
        ref={ref}
        className={`w-full bg-card border ${error ? 'border-danger' : 'border-border'} text-white placeholder-muted px-4 py-3 text-sm focus:outline-none focus:border-accent transition-colors ${className}`}
        {...rest}
      />
      {error && <p className="text-xs text-danger">{error}</p>}
      {hint && !error && <p className="text-xs text-muted">{hint}</p>}
    </div>
  )
)
Input.displayName = 'Input'
