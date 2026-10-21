import type { AccountSummary } from '@/components/shell/account-menu'
import { SiteHeader, SiteSidebar } from '@/components/shell/site-header'
import { getServerProfile } from '@/lib/ledger/server-service'
import { LedgerError } from '@/lib/ledger/types'
import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  if (!(await cookies()).has('ledgerchain_session')) redirect('/login')

  let profile
  try {
    profile = await getServerProfile()
  } catch (error) {
    if (error instanceof LedgerError && error.code === 'AUTHENTICATION_REQUIRED') redirect('/login')
    throw error
  }
  const account: AccountSummary = {
    name: profile.name,
    company: profile.company,
    email: profile.email,
  }

  return (
    <div className="flex min-h-dvh">
      <SiteSidebar account={account} />
      <div className="flex min-w-0 flex-1 flex-col">
        <SiteHeader account={account} />
        <main
          id="main"
          tabIndex={-1}
          className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-6 outline-none sm:py-8 md:px-8 lg:py-10"
        >
          {children}
        </main>
      </div>
    </div>
  )
}
