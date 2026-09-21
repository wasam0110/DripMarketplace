import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/api/auth.api'
import { useAuthStore } from '@/store/authStore'

export function useMe() {
  const { accessToken } = useAuthStore()
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn:  authApi.me,
    enabled:  !!accessToken,
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const { setAuth } = useAuthStore()
  const navigate    = useNavigate()
  return useMutation({
    mutationFn: authApi.login,
    onSuccess:  ({ access_token, user }) => {
      setAuth(access_token, user)
      if (user.role === 'admin')  navigate('/admin')
      else if (user.role === 'seller') navigate('/dashboard')
      else navigate('/account')
    },
  })
}

export function useLogout() {
  const { logout } = useAuthStore()
  const qc         = useQueryClient()
  const navigate   = useNavigate()
  return useMutation({
    mutationFn: authApi.logout,
    onSettled:  () => { logout(); qc.clear(); navigate('/') },
  })
}

export function useRegister() {
  return useMutation({ mutationFn: authApi.register })
}
