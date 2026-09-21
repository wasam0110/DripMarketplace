import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowUpRight } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useRegister } from '@/hooks/useAuth'
import { getErrorMessage } from '@/utils/errorHandler'
import { useState } from 'react'

const schema = z.object({
  first_name: z.string().min(2).max(100),
  last_name:  z.string().min(2).max(100),
  email:      z.string().email(),
  password:   z.string().min(8).regex(/(?=.*[A-Z])(?=.*[a-z])(?=.*\d)/, 'Must include uppercase, lowercase, and number'),
  phone:      z.string().optional(),
})
type FormValues = z.infer<typeof schema>

export default function RegisterPage() {
  const [done, setDone] = useState(false)
  const register_    = useRegister()
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema) })

  if (done) return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="text-center flex flex-col gap-4">
        <p className="text-accent text-4xl font-bold font-mono">✓</p>
        <h2 className="font-bold text-xl">Account created.</h2>
        <p className="text-muted text-sm">Check your email to verify before signing in.</p>
        <Link to="/login" className="btn-primary self-center">Go to sign in <ArrowUpRight size={15} /></Link>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm flex flex-col gap-8">
        <div>
          <Link to="/" className="font-mono font-bold text-2xl">DRIP<span className="text-accent">.</span></Link>
          <h1 className="text-2xl font-bold mt-6">Join the drop.</h1>
          <p className="text-muted text-sm mt-1">Create your account and keep every independent label in reach.</p>
        </div>

        <form onSubmit={handleSubmit(d => register_.mutate(d, { onSuccess: () => setDone(true) }))} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="First name" error={errors.first_name?.message} {...register('first_name')} />
            <Input label="Last name"  error={errors.last_name?.message}  {...register('last_name')} />
          </div>
          <Input label="Email"    type="email"    autoComplete="email"       error={errors.email?.message}    {...register('email')} />
          <Input label="Password" type="password" autoComplete="new-password" error={errors.password?.message} {...register('password')} />
          <Input label="Phone (optional)" error={errors.phone?.message} {...register('phone')} placeholder="03001234567" />

          {register_.error && <p className="text-xs text-danger">{getErrorMessage(register_.error)}</p>}

          <Button type="submit" loading={register_.isPending} className="w-full justify-center mt-2">
            Create account <ArrowUpRight size={15} />
          </Button>
        </form>

        <p className="text-xs text-muted text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-white hover:text-accent">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
