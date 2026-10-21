import 'server-only'
import { cookies } from 'next/headers'
import {
  activityFromBackend,
  pageQuery,
  profileFromBackend,
  serverApiBase,
  serverRequest,
  type BackendActivity,
  type BackendAsset,
  type BackendBlockchainStatus,
  type BackendEvent,
  type BackendFinanceBudget,
  type BackendPaymentRequest,
  type BackendInventoryBatch,
  type BackendInventoryShipment,
  type BackendInventoryMovement,
  type BackendInventoryStock,
  type BackendNotifications,
  type BackendOrganization,
  type BackendOwnership,
  type BackendPage,
  type BackendProduct,
  type BackendSettings,
  type BackendUser,
  type BackendVerification,
} from './api-client'
import type { AccountPreferences, ActivityKind, ActivityRecord } from './types'

async function request<T>(path: string) {
  return serverRequest<T>(path, { apiBase: serverApiBase(), cookieHeader: (await cookies()).toString() })
}

export async function getServerProfile() {
  const [user, account] = await Promise.all([
    request<BackendUser>('/users/me'),
    request<BackendOrganization>('/account'),
  ])
  return profileFromBackend(user, account)
}

export async function getServerAccount() {
  return request<BackendOrganization>('/account')
}

export async function getServerPreferences(): Promise<AccountPreferences> {
  const [settings, notifications] = await Promise.all([
    request<BackendSettings>('/users/me/settings'),
    request<BackendNotifications>('/users/me/notifications'),
  ])
  return {
    timeZone: settings.time_zone,
    dateFormat: settings.date_format,
    showTechnicalByDefault: settings.show_technical_by_default,
    notifyPayments: notifications.transaction_notifications,
    notifySecurity: notifications.security_notifications,
    notifyProductUpdates: notifications.marketing_notifications,
    shareUsageData: settings.share_usage_data,
  }
}

export async function getServerActivity(options?: { limit?: number; offset?: number; kinds?: ActivityKind[] }): Promise<{
  records: ActivityRecord[]
  hasMore: boolean
  limit: number
  offset: number
}> {
  const limit = Math.min(Math.max(options?.limit ?? 50, 1), 100)
  const offset = Math.max(options?.offset ?? 0, 0)
  const type = options?.kinds?.length === 1 ? `&type=${encodeURIComponent(options.kinds[0])}` : ''
  const page = await request<BackendPage<BackendActivity>>(`/activity${pageQuery(limit, offset)}${type}`)
  return { records: page.items.map(activityFromBackend), hasMore: page.has_more, limit: page.limit, offset: page.offset }
}

export async function getServerProducts() {
  return request<BackendPage<BackendProduct>>(`/products${pageQuery(50, 0)}`)
}

export async function getServerProduct(id: string) {
  return request<BackendProduct>(`/products/${encodeURIComponent(id)}`)
}

export async function getServerAssets() {
  return request<BackendPage<BackendAsset>>(`/assets${pageQuery(50, 0)}`)
}

export async function getServerAssetDetail(id: string) {
  const encoded = encodeURIComponent(id)
  const [asset, history, ownership, verification, blockchainStatus] = await Promise.all([
    request<BackendAsset>(`/assets/${encoded}`),
    request<BackendPage<BackendEvent>>(`/assets/${encoded}/history${pageQuery(50, 0)}`),
    request<BackendPage<BackendOwnership>>(`/assets/${encoded}/ownership${pageQuery(50, 0)}`),
    request<BackendVerification>(`/assets/${encoded}/verify`),
    request<BackendBlockchainStatus>('/blockchain/status'),
  ])
  return {
    asset,
    history: history.items,
    historyHasMore: history.has_more,
    ownership: ownership.items,
    ownershipHasMore: ownership.has_more,
    verification,
    blockchainStatus,
  }
}

export async function getServerAssetsPageData() {
  const [assets, products] = await Promise.all([getServerAssets(), getServerProducts()])
  return {
    assets: assets.items,
    products: products.items,
    hasMoreAssets: assets.has_more,
  }
}

export async function getServerInventoryPageData() {
  const [stocks, movements, products, batches, shipments, account, blockchainStatus] = await Promise.all([
    request<BackendPage<BackendInventoryStock>>(`/inventory/stocks${pageQuery(50, 0)}`),
    request<BackendPage<BackendInventoryMovement>>(`/inventory/movements${pageQuery(50, 0)}`),
    getServerProducts(),
    request<BackendInventoryBatch[]>(`/inventory/batches${pageQuery(50, 0)}`),
    request<BackendPage<BackendInventoryShipment>>(`/inventory/shipments${pageQuery(50, 0)}`),
    getServerAccount(),
    request<BackendBlockchainStatus>('/blockchain/status'),
  ])
  return {
    stocks: stocks.items,
    movements: movements.items,
    products: products.items.filter((product) => product.status === 'active'),
    batches,
    shipments: shipments.items,
    organizationId: account.id,
    organizationName: account.name,
    organizationAccountNumber: account.account_number,
    organizationRole: account.role,
    blockchainStatus,
    hasMoreStocks: stocks.has_more,
    hasMoreMovements: movements.has_more,
    hasMoreShipments: shipments.has_more,
  }
}

export async function getServerPageData() {
  const [profile, account, activity] = await Promise.all([
    getServerProfile(),
    getServerAccount(),
    getServerActivity({ limit: 50 }),
  ])
  return { profile, account, ...activity }
}

export async function getServerFinancePageData() {
  const [account, budgets, requests] = await Promise.all([
    getServerAccount(),
    request<BackendPage<BackendFinanceBudget>>(`/finance/budgets${pageQuery(50, 0)}`),
    request<BackendPage<BackendPaymentRequest>>(`/finance/payment-requests${pageQuery(50, 0)}`),
  ])
  return { account, budgets: budgets.items, requests: requests.items }
}
