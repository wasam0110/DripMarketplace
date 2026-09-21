import { Link, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowUpRight } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useLogin } from '@/hooks/useAuth'
import { getErrorMessage } from '@/utils/errorHandler'

const schema = z.object({ email: z.string().email(), password: z.string().min(1) })
type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const login    = useLogin()
  const location = useLocation()
  const from     = (location.state as { from?: string })?.from || '/'
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema) })

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm flex flex-col gap-8">
        <div>
          <Link to="/" className="font-mono font-bold text-2xl">DRIP<span className="text-accent">.</span></Link>
          <h1 className="text-2xl font-bold mt-6">Welcome back.</h1>
          <p className="text-muted text-sm mt-1">Sign in to manage orders, products, and your account.</p>
        </div>

        <form onSubmit={handleSubmit(d => login.mutate(d))} className="flex flex-col gap-4">
          <Input label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register('email')} />
          <Input label="Password" type="password" autoComplete="current-password" error={errors.password?.message} {...register('password')} />

          {login.error && <p className="text-xs text-danger">{getErrorMessage(login.error)}</p>}

          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-xs text-muted hover:text-white">Forgot password?</Link>
          </div>

          <Button type="submit" loading={login.isPending} className="w-full justify-center">
            Sign in <ArrowUpRight size={15} />
          </Button>
        </form>

        <p className="text-xs text-muted text-center">
          New to DRIP?{' '}
          <Link to="/register" className="text-white hover:text-accent">Create an account</Link>
        </p>
      </div>
    </div>
  )
}
