import type { Metadata } from 'next'
import { SettingsForm } from '@/components/account/settings-form'
import { PageHeader } from '@/components/ledger/page-header'
import { getServerPreferences } from '@/lib/ledger/server-service'

export const metadata: Metadata = { title: 'Settings' }

export default async function SettingsPage() {
  const preferences = await getServerPreferences()
  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title="Settings"
        description="Appearance, language, and how LedgerChain keeps you informed."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Settings' }]}
      />
      <SettingsForm initialPreferences={preferences} />
    </div>
  )
}
