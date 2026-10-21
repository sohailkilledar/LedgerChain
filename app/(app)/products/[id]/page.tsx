import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeftIcon } from 'lucide-react'
import { PageHeader } from '@/components/ledger/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getServerProduct } from '@/lib/ledger/server-service'
import { formatDateTime } from '@/lib/ledger/format'

export const metadata: Metadata = { title: 'Product details' }

export default async function ProductDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const product = await getServerProduct(id)

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title={product.name}
        description="A product and SKU record connecting your organization’s inventory with individually tracked assets."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Products', href: '/products' }, { label: product.sku }]}
      />
      <Card>
        <CardHeader>
          <CardTitle>{product.name}</CardTitle>
          <CardDescription>{product.category} · SKU {product.sku}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {product.description && <p className="text-sm leading-relaxed">{product.description}</p>}
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div><dt className="text-xs text-muted-foreground">Catalog quantity</dt><dd className="mt-1 font-medium">{product.quantity ?? 'Not specified'}{product.unit ? ` ${product.unit}` : ''}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Status</dt><dd className="mt-1 font-medium capitalize">{product.status}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Organization</dt><dd className="mt-1 break-all font-mono text-xs">{product.organization_id}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Created</dt><dd className="mt-1 text-sm">{formatDateTime(product.created_at)}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Last updated</dt><dd className="mt-1 text-sm">{formatDateTime(product.updated_at)}</dd></div>
          </dl>
          <p className="break-all border-t pt-4 font-mono text-xs text-muted-foreground">Product ID: {product.id}</p>
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <Button variant="outline" render={<Link href="/inventory" />} nativeButton={false}>Open organization inventory</Button>
            <Button variant="outline" render={<Link href="/assets" />} nativeButton={false}>Browse registered assets</Button>
            <Button variant="ghost" className="sm:ml-auto" render={<Link href="/products" />} nativeButton={false}>
              <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" /> Back to products
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
