import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { LoginForm } from '@/components/auth/login-form'
import { serverApiBase, serverRequest } from '@/lib/ledger/api-client'

export const metadata: Metadata = { title: 'Sign in' }

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; registered?: string }> }) {
  const { next, registered } = await searchParams
  const cookieStore = await cookies()
  let authenticated = false

  if (cookieStore.has('ledgerchain_session')) {
    try {
      await serverRequest('/auth/me', { apiBase: serverApiBase(), cookieHeader: cookieStore.toString() })
      authenticated = true
    } catch {
      // Keep the login form available if session validation fails.
    }
  }

  if (authenticated) redirect('/')

  const nextPath = next === '/profile?setup=1' ? next : '/'
  return <LoginForm nextPath={nextPath} registrationComplete={registered === '1'} />
}
