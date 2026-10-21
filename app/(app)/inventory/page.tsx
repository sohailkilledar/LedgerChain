import type { Metadata } from 'next'
import { InventoryManager } from '@/components/inventory/inventory-manager'
import { SupplyChainManager } from '@/components/inventory/supply-chain-manager'
import { PageHeader } from '@/components/ledger/page-header'
import { getServerInventoryPageData } from '@/lib/ledger/server-service'

export const metadata: Metadata = {
  title: 'Inventory & Traceability',
  description: 'Manage product batches, stock by location, and auditable shipment receipts between organizations.',
}

export default async function InventoryPage() {
  const { stocks, movements, products, batches, shipments, organizationId, organizationName, organizationAccountNumber, organizationRole, blockchainStatus, hasMoreStocks, hasMoreMovements, hasMoreShipments } = await getServerInventoryPageData()

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title="Inventory"
        description="Track available product stock by location with an auditable history of every change."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Inventory' }]}
      />
      <SupplyChainManager
        initialBatches={batches}
        initialShipments={shipments}
        products={products}
        organizationId={organizationId}
        organizationName={organizationName}
        organizationAccountNumber={organizationAccountNumber}
        organizationRole={organizationRole}
        blockchainStatus={blockchainStatus}
        initialHasMoreShipments={hasMoreShipments}
      />
      <InventoryManager
        initialStocks={stocks}
        initialMovements={movements}
        products={products}
        batches={batches}
        initialHasMoreStocks={hasMoreStocks}
        initialHasMoreMovements={hasMoreMovements}
      />
    </div>
  )
}
