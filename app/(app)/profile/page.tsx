import type { Metadata } from 'next'
import { ProfileForm } from '@/components/account/profile-form'
import { PageHeader } from '@/components/ledger/page-header'
import { getServerProfile } from '@/lib/ledger/server-service'

export const metadata: Metadata = { title: 'Profile' }

export default async function ProfilePage({ searchParams }: { searchParams: Promise<{ setup?: string }> }) {
  const [profile, params] = await Promise.all([getServerProfile(), searchParams])
  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title="Profile"
        description="Your name and business details as they appear on records you create."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Profile' }]}
      />
      <ProfileForm initialProfile={profile} completeSetup={params.setup === '1'} />
    </div>
  )
}
