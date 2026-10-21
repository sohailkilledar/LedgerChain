import type { Metadata } from 'next'
import { PageHeader } from '@/components/ledger/page-header'
import { AssetDetail } from '@/components/assets/asset-detail'
import { getServerAssetDetail } from '@/lib/ledger/server-service'

export const metadata: Metadata = { title: 'Asset details' }

export default async function AssetDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const { asset, history, historyHasMore, ownership, ownershipHasMore, verification, blockchainStatus } = await getServerAssetDetail(id)

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title={asset.name}
        description="Review ownership, custody, provenance history, and backend verification results."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Assets', href: '/assets' }, { label: asset.asset_identifier }]}
      />
      <AssetDetail
        initialAsset={asset}
        initialHistory={history}
        initialHasMoreHistory={historyHasMore}
        initialOwnership={ownership}
        initialHasMoreOwnership={ownershipHasMore}
        initialVerification={verification}
        initialBlockchainStatus={blockchainStatus}
      />
    </div>
  )
}
