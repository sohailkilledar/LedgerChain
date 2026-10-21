import { LedgerError, type AccountPreferences, type AccountProfile, type ActivityKind, type ActivityRecord, type AppNotification, type PaymentDraft, type PaymentStage, type ProfileUpdate, type SecurityOverview, type SignInInput, type SignUpInput, type SupportRequestInput } from './types'
import { activityFromBackend, backendNotificationPayload, backendSettingsPayload, newIdempotencyKey, pageQuery, paymentFromBackend, preferencesFromBackend, profileFromBackend, requestJson, unsupportedOperation, type BackendActivity, type BackendAsset, type BackendBlockchainRecord, type BackendBlockchainStatus, type BackendEvent, type BackendShipmentEventVerification, type BackendFinanceBudget, type BackendInventoryBatch, type BackendInventoryShipment, type BackendInventoryMovement, type BackendInventoryStock, type BackendNotifications, type BackendOrganization, type BackendOwnership, type BackendPage, type BackendPayment, type BackendPaymentRequest, type BackendPaymentRequestEvent, type BackendProduct, type BackendSettings, type BackendUser, type BackendVerification, type FinanceBudgetInput, type PaymentRequestInput, type InventoryMovementRequest, type InventoryBatchInput, type InventoryShipmentInput, type ProductCreateRequest, type AssetCreateRequest, type ResendResult, type SignupResult } from './api-client'

export interface LedgerService {
  listActivity(options?: { kinds?: ActivityKind[]; limit?: number; offset?: number }): Promise<ActivityRecord[]>
  listActivityPage(options?: { kinds?: ActivityKind[]; limit?: number; offset?: number }): Promise<ActivityPage>
  submitPayment(draft: PaymentDraft, options?: { onStage?: (stage: PaymentStage) => void; idempotencyKey?: string }): Promise<ActivityRecord>
  getProfile(): Promise<AccountProfile>
  updateProfile(update: ProfileUpdate): Promise<AccountProfile>
  getAccount(): Promise<BackendOrganization>
  getPreferences(): Promise<AccountPreferences>
  updatePreferences(update: AccountPreferences): Promise<AccountPreferences>
  listNotifications(): Promise<AppNotification[]>
  markNotificationsRead(ids: string[]): Promise<void>
  getSecurityOverview(): Promise<SecurityOverview>
  changePassword(input: { currentPassword: string; newPassword: string }): Promise<void>
  signOutOtherSessions(): Promise<void>
  signIn(input: SignInInput): Promise<void>
  signUp(input: SignUpInput): Promise<SignupResult>
  requestPasswordReset(email: string): Promise<ResendResult>
  resetPassword(input: { password: string; token?: string }): Promise<void>
  resendVerification(email: string): Promise<ResendResult>
  verifyEmail(token: string): Promise<void>
  signOut(): Promise<void>
  sendSupportRequest(input: SupportRequestInput): Promise<{ ticketId: string }>
  listProducts(options?: { limit?: number; offset?: number }): Promise<BackendProduct[]>
  listProductPage(options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendProduct>>
  createProduct(input: Omit<ProductCreateRequest, 'organization_id'>): Promise<BackendProduct>
  listAssets(options?: { limit?: number; offset?: number }): Promise<BackendAsset[]>
  listAssetPage(options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendAsset>>
  createAsset(input: Omit<AssetCreateRequest, 'organization_id'>): Promise<BackendAsset>
  getAsset(id: string): Promise<BackendAsset>
  getAssetHistory(id: string, options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendEvent>>
  getAssetOwnership(id: string, options?: { limit?: number; offset?: number }): Promise<BackendPage<{ id: string; asset_id: string; organization_id: string; event_id: string; created_at: string }>>
  verifyAsset(id: string): Promise<BackendVerification>
  transferAsset(id: string, recipientAccountNumber: string, idempotencyKey?: string): Promise<BackendEvent>
  changeAssetCustody(id: string, custodianAccountNumber: string, idempotencyKey?: string): Promise<BackendEvent>
  retireAsset(id: string, idempotencyKey?: string): Promise<BackendEvent>
  anchorAssetEvent(assetId: string, eventId: string): Promise<BackendBlockchainRecord>
  anchorShipmentEvent(shipmentId: string, eventId: string): Promise<BackendBlockchainRecord>
  verifyShipmentEvent(shipmentId: string, eventId: string): Promise<BackendShipmentEventVerification>
  getBlockchainStatus(): Promise<BackendBlockchainStatus>
  listInventoryStockPage(options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendInventoryStock>>
  listInventoryMovementPage(options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendInventoryMovement>>
  createInventoryMovement(input: Omit<InventoryMovementRequest, 'organization_id'>, idempotencyKey?: string): Promise<BackendInventoryMovement>
  listInventoryBatches(options?: { limit?: number; offset?: number }): Promise<BackendInventoryBatch[]>
  createInventoryBatch(input: Omit<InventoryBatchInput, 'organization_id'>): Promise<BackendInventoryBatch>
  listInventoryShipments(options?: { limit?: number; offset?: number }): Promise<BackendPage<BackendInventoryShipment>>
  createInventoryShipment(input: Omit<InventoryShipmentInput, 'organization_id'>, idempotencyKey?: string): Promise<BackendInventoryShipment>
  transitionInventoryShipment(id: string, action: 'dispatch' | 'transit' | 'receive' | 'reject', input?: { destination_location?: string; reason?: string }, idempotencyKey?: string): Promise<BackendInventoryShipment>
  listFinanceBudgets(options?: { limit?: number; offset?: number }): Promise<BackendFinanceBudget[]>
  listPaymentRequests(options?: { limit?: number; offset?: number }): Promise<BackendPaymentRequest[]>
  createFinanceBudget(input: FinanceBudgetInput): Promise<BackendFinanceBudget>
  createPaymentRequest(input: PaymentRequestInput, idempotencyKey?: string): Promise<BackendPaymentRequest>
  submitPaymentRequest(requestId: string): Promise<BackendPaymentRequest>
  decidePaymentRequest(requestId: string, decision: 'approve' | 'reject', note?: string): Promise<BackendPaymentRequest>
  executePaymentRequest(requestId: string): Promise<BackendPaymentRequest>
  getPaymentRequestHistory(requestId: string): Promise<BackendPaymentRequestEvent[]>
}

const json = (value: unknown) => JSON.stringify(value)

export type ActivityPage = { records: ActivityRecord[]; hasMore: boolean; limit: number; offset: number }

async function fetchActivityPage(options?: { kinds?: ActivityKind[]; limit?: number; offset?: number }): Promise<ActivityPage> {
  const limit = Math.min(Math.max(options?.limit ?? 100, 1), 100)
  const offset = Math.max(options?.offset ?? 0, 0)
  const type = options?.kinds?.length === 1 ? `&type=${encodeURIComponent(options.kinds[0])}` : ''
  const page = await requestJson<BackendPage<BackendActivity>>(`/activity${pageQuery(limit, offset)}${type}`)
  return { records: page.items.map(activityFromBackend), hasMore: page.has_more, limit: page.limit, offset: page.offset }
}

async function getProductPage(options?: { limit?: number; offset?: number }) {
  return requestJson<BackendPage<BackendProduct>>(`/products${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)
}

async function getAssetPage(options?: { limit?: number; offset?: number }) {
  return requestJson<BackendPage<BackendAsset>>(`/assets${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)
}

async function getInventoryStockPage(options?: { limit?: number; offset?: number }) {
  return requestJson<BackendPage<BackendInventoryStock>>(`/inventory/stocks${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)
}

async function getInventoryMovementPage(options?: { limit?: number; offset?: number }) {
  return requestJson<BackendPage<BackendInventoryMovement>>(`/inventory/movements${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)
}

async function getProfileFromApi() {
  const [user, account] = await Promise.all([
    requestJson<BackendUser>('/users/me'),
    requestJson<BackendOrganization>('/account'),
  ])
  return profileFromBackend(user, account)
}

async function getPrefsFromApi() {
  const [settings, notifications] = await Promise.all([
    requestJson<BackendSettings>('/users/me/settings'),
    requestJson<BackendNotifications>('/users/me/notifications'),
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

export const ledgerService: LedgerService = {
  async listActivity(options) {
    return (await fetchActivityPage(options)).records
  },

  listActivityPage: fetchActivityPage,

  async submitPayment(draft, options) {
    options?.onStage?.('submitted')
    options?.onStage?.('recording')
    const payment = await requestJson<BackendPayment>('/payments', {
      method: 'POST',
      body: json({ recipient_account: draft.recipientAccount, amount: draft.amount, currency: 'INR', purpose: draft.purpose, ...(draft.note ? { note: draft.note } : {}) }),
      idempotencyKey: options?.idempotencyKey ?? newIdempotencyKey(),
    })
    const record = paymentFromBackend(payment)
    options?.onStage?.('completed')
    return record
  },

  getProfile: getProfileFromApi,

  async updateProfile(update) {
    if (update.email !== (await requestJson<BackendUser>('/users/me')).email) {
      throw new LedgerError({ code: 'EMAIL_READ_ONLY', message: 'Email address changes are not supported by the backend profile API.', retryable: false, committed: false })
    }
    const profile = await requestJson<BackendUser>('/users/me', { method: 'PATCH', body: json({ display_name: update.name, phone: update.phone ?? null }) })
    let account: BackendOrganization
    try {
      account = await requestJson<BackendOrganization>('/account', { method: 'PATCH', body: json({ name: update.company }) })
    } catch (error) {
      throw new LedgerError({
        code: 'PROFILE_PARTIAL_UPDATE',
        message: `Your personal details were saved, but the business account update could not be confirmed. Retry to finish saving. ${error instanceof Error ? error.message : ''}`.trim(),
        retryable: true,
        committed: true,
        outcomeUnknown: error instanceof LedgerError ? error.outcomeUnknown : undefined,
      })
    }
    return profileFromBackend(profile, account)
  },

  getAccount: () => requestJson<BackendOrganization>('/account'),
  getPreferences: getPrefsFromApi,

  async updatePreferences(update) {
    const settings = await requestJson<BackendSettings>('/users/me/settings', { method: 'PATCH', body: json(backendSettingsPayload(update)) })
    let notifications: BackendNotifications
    try {
      notifications = await requestJson<BackendNotifications>('/users/me/notifications', { method: 'PATCH', body: json(backendNotificationPayload(update)) })
    } catch (error) {
      throw new LedgerError({
        code: 'PREFERENCES_PARTIAL_UPDATE',
        message: `General preferences were saved, but notification preferences could not be confirmed. Retry to finish saving. ${error instanceof Error ? error.message : ''}`.trim(),
        retryable: true,
        committed: true,
        outcomeUnknown: error instanceof LedgerError ? error.outcomeUnknown : undefined,
      })
    }
    return {
      timeZone: settings.time_zone,
      dateFormat: settings.date_format,
      showTechnicalByDefault: settings.show_technical_by_default,
      notifyPayments: notifications.transaction_notifications,
      notifySecurity: notifications.security_notifications,
      notifyProductUpdates: notifications.marketing_notifications,
      shareUsageData: settings.share_usage_data,
    }
  },

  async listNotifications() { return [] },
  async markNotificationsRead() {},
  async getSecurityOverview() { return unsupportedOperation('Security overview is not available because the backend has no session-history API.') },
  async changePassword() { return unsupportedOperation('Password changes are not available because the backend has no authenticated change-password API.') },
  async signOutOtherSessions() { return unsupportedOperation('Session management is not available because the backend has no session-revocation endpoint for other sessions.') },

  async signIn(input) {
    await requestJson('/auth/login', { method: 'POST', body: json({ email: input.email, password: input.password, remember: input.remember }) })
  },

  async signUp(input) {
    return requestJson<SignupResult>('/auth/register', { method: 'POST', body: json({ email: input.email, password: input.password }) })
  },

  async requestPasswordReset(email) {
    return requestJson<ResendResult>('/auth/forgot-password', { method: 'POST', body: json({ email }) })
  },

  async resetPassword(input) {
    if (!input.token) throw new LedgerError({ code: 'RESET_TOKEN_REQUIRED', message: 'Open the password-reset link and enter its token to continue.', retryable: false, committed: false })
    await requestJson('/auth/reset-password', { method: 'POST', body: json({ token: input.token, password: input.password }) })
  },

  async resendVerification(email) {
    return requestJson<ResendResult>('/auth/resend-verification', { method: 'POST', body: json({ email }) })
  },

  async verifyEmail(token) {
    await requestJson('/auth/verify-email', { method: 'POST', body: json({ token }) })
  },

  async signOut() { await requestJson('/auth/logout', { method: 'POST' }) },
  async sendSupportRequest() { return unsupportedOperation('Support tickets are not available because the backend does not expose a support-ticket API.') },

  async listProducts(options) {
    return (await getProductPage(options)).items
  },
  listProductPage: getProductPage,
  async createProduct(input) {
    const account = await requestJson<BackendOrganization>('/account')
    return requestJson<BackendProduct>('/products', { method: 'POST', body: json({ ...input, organization_id: account.id }) })
  },
  async listAssets(options) {
    return (await getAssetPage(options)).items
  },
  listAssetPage: getAssetPage,
  async createAsset(input) {
    const account = await requestJson<BackendOrganization>('/account')
    return requestJson<BackendAsset>('/assets', { method: 'POST', body: json({ ...input, organization_id: account.id }) })
  },
  getAsset: (id) => requestJson<BackendAsset>(`/assets/${encodeURIComponent(id)}`),
  getAssetHistory: (id, options) => requestJson<BackendPage<BackendEvent>>(`/assets/${encodeURIComponent(id)}/history${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`),
  getAssetOwnership: (id, options) => requestJson<BackendPage<BackendOwnership>>(`/assets/${encodeURIComponent(id)}/ownership${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`),
  verifyAsset: (id) => requestJson<BackendVerification>(`/assets/${encodeURIComponent(id)}/verify`),
  transferAsset: (id, recipientAccountNumber, idempotencyKey = newIdempotencyKey()) => requestJson(`/assets/${encodeURIComponent(id)}/transfer`, { method: 'POST', body: json({ recipient_account_number: recipientAccountNumber }), idempotencyKey }),
  changeAssetCustody: (id, custodianAccountNumber, idempotencyKey = newIdempotencyKey()) => requestJson(`/assets/${encodeURIComponent(id)}/custody`, { method: 'POST', body: json({ custodian_account_number: custodianAccountNumber }), idempotencyKey }),
  retireAsset: (id, idempotencyKey = newIdempotencyKey()) => requestJson(`/assets/${encodeURIComponent(id)}/retire`, { method: 'POST', body: json({ status: 'retired' }), idempotencyKey }),
  anchorAssetEvent: (assetId, eventId) => requestJson<BackendBlockchainRecord>(`/assets/${encodeURIComponent(assetId)}/history/${encodeURIComponent(eventId)}/anchor`, { method: 'POST' }),
  anchorShipmentEvent: (shipmentId, eventId) => requestJson<BackendBlockchainRecord>(`/blockchain/shipments/${encodeURIComponent(shipmentId)}/events/${encodeURIComponent(eventId)}/anchor`, { method: 'POST' }),
  verifyShipmentEvent: (shipmentId, eventId) => requestJson<BackendShipmentEventVerification>(`/blockchain/shipments/${encodeURIComponent(shipmentId)}/events/${encodeURIComponent(eventId)}/verify`),
  getBlockchainStatus: () => requestJson<BackendBlockchainStatus>('/blockchain/status'),
  listInventoryStockPage: getInventoryStockPage,
  listInventoryMovementPage: getInventoryMovementPage,
  async createInventoryMovement(input, idempotencyKey = newIdempotencyKey()) {
    const account = await requestJson<BackendOrganization>('/account')
    return requestJson<BackendInventoryMovement>('/inventory/movements', {
      method: 'POST',
      body: json({ ...input, organization_id: account.id }),
      idempotencyKey,
    })
  },
  async listInventoryBatches(options) {
    return requestJson<BackendInventoryBatch[]>(`/inventory/batches${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)
  },
  async createInventoryBatch(input) {
    const account = await requestJson<BackendOrganization>('/account')
    return requestJson<BackendInventoryBatch>('/inventory/batches', { method: 'POST', body: json({ ...input, organization_id: account.id }) })
  },
  listInventoryShipments: (options) => requestJson<BackendPage<BackendInventoryShipment>>(`/inventory/shipments${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`),
  async createInventoryShipment(input, idempotencyKey = newIdempotencyKey()) {
    const account = await requestJson<BackendOrganization>('/account')
    return requestJson<BackendInventoryShipment>('/inventory/shipments', { method: 'POST', body: json({ ...input, organization_id: account.id }), idempotencyKey })
  },
  transitionInventoryShipment: (id, action, input = {}, idempotencyKey = newIdempotencyKey()) => requestJson<BackendInventoryShipment>(`/inventory/shipments/${encodeURIComponent(id)}/${action}`, { method: 'POST', body: json(input), idempotencyKey }),
  async listFinanceBudgets(options) {
    return (await requestJson<BackendPage<BackendFinanceBudget>>(`/finance/budgets${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)).items
  },
  async listPaymentRequests(options) {
    return (await requestJson<BackendPage<BackendPaymentRequest>>(`/finance/payment-requests${pageQuery(options?.limit ?? 50, options?.offset ?? 0)}`)).items
  },
  createFinanceBudget: (input) => requestJson<BackendFinanceBudget>('/finance/budgets', { method: 'POST', body: json(input) }),
  createPaymentRequest: (input, idempotencyKey = newIdempotencyKey()) => requestJson<BackendPaymentRequest>('/finance/payment-requests', { method: 'POST', body: json(input), idempotencyKey }),
  submitPaymentRequest: (requestId) => requestJson<BackendPaymentRequest>(`/finance/payment-requests/${encodeURIComponent(requestId)}/submit`, { method: 'POST' }),
  decidePaymentRequest: (requestId, decision, note) => requestJson<BackendPaymentRequest>(`/finance/payment-requests/${encodeURIComponent(requestId)}/${decision}`, { method: 'POST', body: json({ note }) }),
  executePaymentRequest: (requestId) => requestJson<BackendPaymentRequest>(`/finance/payment-requests/${encodeURIComponent(requestId)}/execute`, { method: 'POST' }),
  async getPaymentRequestHistory(requestId) {
    return (await requestJson<{ items: BackendPaymentRequestEvent[] }>(`/finance/payment-requests/${encodeURIComponent(requestId)}/history`)).items
  },
}

export type { AccountPreferences, AccountProfile, ActivityRecord, PaymentDraft, PaymentStage, ProfileUpdate, SecurityOverview, SignInInput, SignUpInput, SupportRequestInput }
export type { BackendAsset, BackendBlockchainRecord, BackendBlockchainStatus, BackendEvent, BackendInventoryBatch, BackendInventoryShipment, BackendInventoryMovement, BackendInventoryStock, BackendOrganization, BackendProduct, BackendVerification }
export { newIdempotencyKey }
export function getNotificationFeedIsEmpty() { return true }
export function unsupportedNotice(message: string) { return message }
export function unusedMockFallback(): never { throw new LedgerError({ code: 'NOT_SUPPORTED', message: 'No frontend-only fallback is available.', retryable: false, committed: false }) }
export function safeErrorMessage(error: unknown) { return error instanceof Error ? error.message : 'The request could not be completed.' }
export function balanceAsString(account: BackendOrganization) { return String(account.balance) }
export function activityLimitQuery(limit: number, offset: number) { return pageQuery(limit, offset) }
export function mapActivity(item: BackendActivity) { return activityFromBackend(item) }
export function mapPayment(payment: BackendPayment) { return paymentFromBackend(payment) }
export function pageHasMore<T>(page: BackendPage<T>) { return page.has_more }
export function getLedgerError(error: unknown) { return error instanceof LedgerError ? error : undefined }
export function adaptProfile(user: BackendUser, organization: BackendOrganization) { return profileFromBackend(user, organization) }
export function adaptPreferences(settings: BackendSettings, notifications: BackendNotifications) { return preferencesFromBackend(settings, notifications) }
export function profileUpdatePayload(update: ProfileUpdate) { return { display_name: update.name, phone: update.phone ?? null } }
export function productRequest(input: Omit<ProductCreateRequest, 'organization_id'>, organizationId: string): ProductCreateRequest { return { ...input, organization_id: organizationId } }
export function assetRequest(input: Omit<AssetCreateRequest, 'organization_id'>, organizationId: string): AssetCreateRequest { return { ...input, organization_id: organizationId } }
export type { ProductCreateRequest, AssetCreateRequest, ResendResult, SignupResult }
