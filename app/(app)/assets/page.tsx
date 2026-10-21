import type { Metadata } from 'next'
import { AssetManager } from '@/components/assets/asset-manager'
import { PageHeader } from '@/components/ledger/page-header'
import { getServerAssetsPageData } from '@/lib/ledger/server-service'

export const metadata: Metadata = { title: 'Assets' }

export default async function AssetsPage() {
  const { assets, products, hasMoreAssets } = await getServerAssetsPageData()
  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader title="Assets" description="Register, transfer, and verify assets using the provenance APIs." breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Assets' }]} />
      <AssetManager initialAssets={assets} products={products} initialHasMore={hasMoreAssets} />
    </div>
  )
}
