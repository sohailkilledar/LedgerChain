import { ArrowRightIcon } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ActivityList } from '@/components/ledger/activity-list'
import { PageHeader } from '@/components/ledger/page-header'
import { AttentionPanel } from '@/components/overview/attention-panel'
import { BalanceSummary } from '@/components/overview/balance-summary'
import { GuidePromo, QuickActions } from '@/components/overview/quick-actions'
import { getServerPageData } from '@/lib/ledger/server-service'

export default async function OverviewPage() {
  const { records, profile, account } = await getServerPageData()
  const firstName = profile.name.split(' ')[0]
  const attentionRecords = records.filter((record) => record.status === 'action_required' || record.status === 'failed')

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        eyebrow={profile.company}
        title={`Welcome back, ${firstName}`}
        description="Review your internal finance, shipment, inventory, ownership, and verification records."
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-6">
        <BalanceSummary account={account} />
        <AttentionPanel records={attentionRecords} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-6">
        <Card className="gap-0 py-0">
          <CardHeader className="border-b py-4">
            <CardTitle>
              <h2>Recent activity</h2>
            </CardTitle>
            <CardDescription>Select any item to see its full record.</CardDescription>
            <CardAction>
              <Button variant="ghost" render={<Link href="/activity" />} nativeButton={false}>
                View all
                <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
              </Button>
            </CardAction>
          </CardHeader>
          <ActivityList records={records.slice(0, 5)} />
        </Card>

        <div className="flex flex-col gap-4 lg:gap-6">
          <QuickActions />
          <GuidePromo />
        </div>
      </div>
    </div>
  )
}
