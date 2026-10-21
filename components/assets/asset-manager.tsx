'use client'

import { ArrowUpRightIcon, CirclePlusIcon, PackageSearchIcon } from 'lucide-react'
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
import type { BackendAsset, BackendProduct } from '@/lib/ledger/api-client'

export function AssetManager({ initialAssets, products, initialHasMore }: { initialAssets: BackendAsset[]; products: BackendProduct[]; initialHasMore: boolean }) {
  const router = useRouter()
  const [assets, setAssets] = useState(initialAssets)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [loadingMore, setLoadingMore] = useState(false)
  const [creating, setCreating] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string>()

  async function loadMore() {
    setLoadingMore(true)
    setError(undefined)
    try {
      const page = await ledgerService.listAssetPage({ limit: 50, offset: assets.length })
      setAssets((current) => [...current, ...page.items])
      setHasMore(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load more assets.')
    } finally {
      setLoadingMore(false)
    }
  }

  async function createAsset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    let metadata: Record<string, unknown>
    try {
      metadata = JSON.parse(String(form.get('metadata') || '{}'))
      if (!metadata || Array.isArray(metadata) || typeof metadata !== 'object') throw new Error('Metadata must be a JSON object.')
    } catch {
      setError('Enter metadata as a valid JSON object, such as {"serial_number":"ABC-123"}.')
      return
    }

    setPending(true)
    setError(undefined)
    try {
      const productId = String(form.get('product_id') ?? '')
      const asset = await ledgerService.createAsset({
        asset_identifier: String(form.get('asset_identifier') ?? '').trim(),
        name: String(form.get('name') ?? '').trim(),
        category: String(form.get('category') ?? '').trim(),
        description: String(form.get('description') ?? '').trim() || undefined,
        product_id: productId || undefined,
        metadata,
      })
      setAssets((current) => [asset, ...current])
      setCreating(false)
      formElement.reset()
      router.refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The asset could not be registered.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">Asset ownership, custody, and provenance are recorded independently.</p>
        <Button onClick={() => setCreating((open) => !open)}>
          <CirclePlusIcon data-icon="inline-start" aria-hidden="true" />
          {creating ? 'Close form' : 'Register asset'}
        </Button>
      </div>

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle>Register an asset</CardTitle>
            <CardDescription>Metadata is stored as a JSON object and becomes part of the asset record.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createAsset} className="flex flex-col gap-5">
              <FieldGroup>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="asset-identifier">Asset identifier</FieldLabel>
                    <Input id="asset-identifier" name="asset_identifier" required maxLength={96} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="asset-name">Name</FieldLabel>
                    <Input id="asset-name" name="name" required maxLength={160} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="asset-category">Category</FieldLabel>
                    <Input id="asset-category" name="category" required maxLength={80} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="asset-product">Related product</FieldLabel>
                    <select id="asset-product" name="product_id" className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                      <option value="">No linked product</option>
                      {products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
                    </select>
                  </Field>
                </div>
                <Field>
                  <FieldLabel htmlFor="asset-description">Description</FieldLabel>
                  <Textarea id="asset-description" name="description" rows={2} maxLength={2000} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="asset-metadata">Metadata (JSON)</FieldLabel>
                  <Textarea id="asset-metadata" name="metadata" rows={3} defaultValue="{}" spellCheck={false} />
                </Field>
              </FieldGroup>
              {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setCreating(false)} disabled={pending}>Cancel</Button>
                <Button type="submit" disabled={pending}>{pending ? 'Registering…' : 'Create asset record'}</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {error && !creating && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {assets.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {assets.map((asset) => (
            <Card key={asset.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1">
                    <CardTitle>{asset.name}</CardTitle>
                    <CardDescription>{asset.category} · {asset.asset_identifier}</CardDescription>
                  </div>
                  <PackageSearchIcon className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {asset.description && <p className="text-sm text-muted-foreground">{asset.description}</p>}
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="text-xs text-muted-foreground">Status</dt><dd className="font-medium capitalize">{asset.status}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Custodian</dt><dd className="truncate font-mono text-xs">{asset.current_custodian_organization_id ?? 'Not assigned'}</dd></div>
                </dl>
                <Button variant="outline" className="self-start" render={<Link href={`/assets/${asset.id}`} />} nativeButton={false}>
                  View history and verify <ArrowUpRightIcon data-icon="inline-end" aria-hidden="true" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <Empty className="py-12">
            <EmptyHeader>
              <EmptyMedia variant="icon"><PackageSearchIcon aria-hidden="true" /></EmptyMedia>
              <EmptyTitle>No assets registered</EmptyTitle>
              <EmptyDescription>Register an individual asset to start an append-only ownership and custody history.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </Card>
      )}
      {hasMore && (
        <Button variant="outline" onClick={loadMore} disabled={loadingMore} className="self-center">
          {loadingMore && <Spinner data-icon="inline-start" />}
          {loadingMore ? 'Loading assets…' : 'Load more assets'}
        </Button>
      )}
    </div>
  )
}
