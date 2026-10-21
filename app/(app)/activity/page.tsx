import type { Metadata } from 'next'
import { PageHeader } from '@/components/ledger/page-header'
import { ActivityBrowser } from '@/components/activity/activity-browser'
import { getServerActivity } from '@/lib/ledger/server-service'

export const metadata: Metadata = {
  title: 'Activity',
}

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ record?: string }>
}) {
  const [activity, { record }] = await Promise.all([getServerActivity({ limit: 50 }), searchParams])

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title="Activity"
        description="Browse persisted finance, payment, inventory, shipment, asset, and blockchain evidence events available to your organization."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Activity' }]}
      />
      <ActivityBrowser records={activity.records} hasMore={activity.hasMore} initialSelectedId={record} />
    </div>
  )
}
