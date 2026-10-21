'use client'

import { ArrowUpRightIcon, CirclePlusIcon, PackageIcon } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService } from '@/lib/ledger/service'
import type { BackendProduct } from '@/lib/ledger/api-client'

export function ProductManager({ initialProducts, initialHasMore }: { initialProducts: BackendProduct[]; initialHasMore: boolean }) {
  const router = useRouter()
  const [products, setProducts] = useState(initialProducts)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [loadingMore, setLoadingMore] = useState(false)
  const [creating, setCreating] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string>()

  async function loadMore() {
    setLoadingMore(true)
    setError(undefined)
    try {
      const page = await ledgerService.listProductPage({ limit: 50, offset: products.length })
      setProducts((current) => [...current, ...page.items])
      setHasMore(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load more products.')
    } finally {
      setLoadingMore(false)
    }
  }

  async function createProduct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    setPending(true)
    setError(undefined)
    try {
      const product = await ledgerService.createProduct({
        sku: String(form.get('sku') ?? '').trim(),
        name: String(form.get('name') ?? '').trim(),
        category: String(form.get('category') ?? '').trim(),
        description: String(form.get('description') ?? '').trim() || undefined,
        quantity: String(form.get('quantity') ?? '').trim() || undefined,
        unit: String(form.get('unit') ?? '').trim() || undefined,
      })
      setProducts((current) => [product, ...current])
      setCreating(false)
      formElement.reset()
      router.refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The product could not be created.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">Use product SKUs to connect receipts, location-based inventory, and individually tracked assets. Catalog quantity is separate from on-hand stock.</p>
        <Button onClick={() => setCreating((open) => !open)}>
          <CirclePlusIcon data-icon="inline-start" aria-hidden="true" />
          {creating ? 'Close form' : 'Add product'}
        </Button>
      </div>

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle>Register a product</CardTitle>
            <CardDescription>Required fields are validated by the backend before the product is stored.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createProduct} className="flex flex-col gap-5">
              <FieldGroup>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="product-sku">SKU</FieldLabel>
                    <Input id="product-sku" name="sku" required maxLength={64} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="product-name">Name</FieldLabel>
                    <Input id="product-name" name="name" required maxLength={160} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="product-category">Category</FieldLabel>
                    <Input id="product-category" name="category" required maxLength={80} />
                  </Field>
                  <div className="grid grid-cols-[minmax(0,1fr)_8rem] gap-3">
                    <Field>
                      <FieldLabel htmlFor="product-quantity">Catalog quantity</FieldLabel>
                      <Input id="product-quantity" name="quantity" inputMode="decimal" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="product-unit">Unit</FieldLabel>
                      <Input id="product-unit" name="unit" maxLength={24} placeholder="pcs" />
                    </Field>
                  </div>
                </div>
                <Field>
                  <FieldLabel htmlFor="product-description">Description</FieldLabel>
                  <Textarea id="product-description" name="description" rows={3} maxLength={2000} />
                </Field>
              </FieldGroup>
              {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setCreating(false)} disabled={pending}>Cancel</Button>
                <Button type="submit" disabled={pending}>{pending ? 'Saving…' : 'Create product'}</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {error && !creating && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {products.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {products.map((product) => (
            <Card key={product.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1">
                    <CardTitle>{product.name}</CardTitle>
                    <CardDescription>{product.category} · SKU {product.sku}</CardDescription>
                  </div>
                  <PackageIcon className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {product.description && <p className="text-sm text-muted-foreground">{product.description}</p>}
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="text-xs text-muted-foreground">Catalog quantity</dt><dd className="font-medium">{product.quantity ?? 'Not specified'}{product.unit ? ` ${product.unit}` : ''}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Status</dt><dd className="font-medium capitalize">{product.status}</dd></div>
                </dl>
                <Button variant="outline" className="self-start" render={<Link href={`/products/${product.id}`} />} nativeButton={false}>
                  View product <ArrowUpRightIcon data-icon="inline-end" aria-hidden="true" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <Empty className="py-12">
            <EmptyHeader>
              <EmptyMedia variant="icon"><PackageIcon aria-hidden="true" /></EmptyMedia>
              <EmptyTitle>No products yet</EmptyTitle>
              <EmptyDescription>Create a product record to organize assets and supply-chain information.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </Card>
      )}
      {hasMore && (
        <Button variant="outline" onClick={loadMore} disabled={loadingMore} className="self-center">
          {loadingMore && <Spinner data-icon="inline-start" />}
          {loadingMore ? 'Loading products…' : 'Load more products'}
        </Button>
      )}
    </div>
  )
}
