import type { Metadata } from 'next'
import { PageHeader } from '@/components/ledger/page-header'
import { ProductManager } from '@/components/products/product-manager'
import { getServerProducts } from '@/lib/ledger/server-service'

export const metadata: Metadata = { title: 'Products' }

export default async function ProductsPage() {
  const products = await getServerProducts()
  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader title="Products" description="Manage organization-scoped product and SKU records that connect inventory locations with individually tracked assets." breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Products' }]} />
      <ProductManager initialProducts={products.items} initialHasMore={products.has_more} />
    </div>
  )
}
