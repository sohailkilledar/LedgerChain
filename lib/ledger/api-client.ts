import { LedgerError } from './types'

export const API_PREFIX = '/api/backend/api/v1'
export type ApiOptions = RequestInit & { idempotencyKey?: string }
type ErrorPayload = { error?: { code?: string; message?: string; retryable?: boolean; committed?: boolean; outcome_unknown?: boolean; request_id?: string; fields?: Array<{ message: string }> } }

export async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const payload = (await response.json().catch(() => ({}))) as ErrorPayload
  if (!response.ok) {
    const error = payload.error
    const validation = error?.fields?.map((field) => field.message).join(' ')
    const message = [error?.message ?? `The request failed (${response.status}).`, validation].filter(Boolean).join(' ')
    throw new LedgerError({
      code: error?.code ?? `HTTP_${response.status}`,
      message: error?.request_id ? `${message} (Request ID: ${error.request_id})` : message,
      retryable: error?.retryable ?? (response.status >= 500 || response.status === 429),
      committed: error?.committed ?? false,
      outcomeUnknown: error?.outcome_unknown ?? false,
    })
  }
  return payload as T
}

function csrfToken() {
  if (typeof document === 'undefined') return undefined
  const cookie = document.cookie.split('; ').find((part) => part.startsWith('ledgerchain_csrf='))
  return cookie ? decodeURIComponent(cookie.slice('ledgerchain_csrf='.length)) : undefined
}

export async function requestJson<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = csrfToken()
    if (csrf) headers.set('X-CSRF-Token', csrf)
    if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey)
  }
  try {
    return await parseResponse<T>(await fetch(`${API_PREFIX}${path}`, { ...options, method, headers, credentials: 'same-origin', cache: 'no-store' }))
  } catch (error) {
    if (error instanceof LedgerError) throw error
    throw new LedgerError({ code: 'API_UNAVAILABLE', message: 'LedgerChain could not reach its API. Check that the backend is running and configured.', retryable: true, committed: false, outcomeUnknown: !['GET', 'HEAD', 'OPTIONS'].includes(method) })
  }
}

export async function serverRequest<T>(path: string, options: RequestInit & { apiBase: string; cookieHeader?: string }) {
  const headers = new Headers(options.headers)
  if (options.cookieHeader) headers.set('Cookie', options.cookieHeader)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  try {
    return await parseResponse<T>(await fetch(`${options.apiBase.replace(/\/$/, '')}/api/v1${path}`, { ...options, headers, cache: 'no-store' }))
  } catch (error) {
    if (error instanceof LedgerError) throw error
    throw new LedgerError({ code: 'API_UNAVAILABLE', message: 'LedgerChain could not reach its API. Check the backend URL and database readiness.', retryable: true, committed: false })
  }
}

export function newIdempotencyKey() { return crypto.randomUUID() }
export function exactMoney(amount: string | number) {
  const normalized = typeof amount === 'number' ? amount.toFixed(2) : amount
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) return '₹0'
  const [whole, fraction = ''] = normalized.split('.')
  const rupees = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(BigInt(whole))
  const paise = fraction.padEnd(2, '0')
  return Number(paise) ? `${rupees}.${paise}` : rupees
}
export function amountMinorUnits(value: string) {
  const [whole, fraction = ''] = value.split('.')
  return BigInt(whole || '0') * 100n + BigInt(fraction.padEnd(2, '0'))
}
export function pageQuery(limit = 100, offset = 0) { return `?limit=${limit}&offset=${offset}` }
export function unsupportedOperation(message: string): never {
  throw new LedgerError({ code: 'NOT_SUPPORTED', message, retryable: false, committed: false })
}

export type BackendPage<T> = { items: T[]; limit: number; offset: number; has_more: boolean }
export type BackendUser = { id: string; email: string; display_name: string | null; phone: string | null; account_status: string; email_verified: boolean; created_at: string; updated_at: string }
export type BackendOrganization = { id: string; name: string; account_number: string; balance: string; account_type: string; status: string; role: string; created_at: string; updated_at: string }
export type BackendSettings = { time_zone: string; locale: string; date_format: 'dmy' | 'mdy' | 'iso'; show_technical_by_default: boolean; share_usage_data: boolean }
export type BackendNotifications = { security_notifications: boolean; transaction_notifications: boolean; account_notifications: boolean; marketing_notifications: boolean }
export type BackendPaymentActivity = { id: string; type: 'payment'; status: 'completed'; title: string; summary: string; direction: 'incoming' | 'outgoing'; amount: string; currency: 'INR'; counterparty: string; counterparty_account: string; timestamp: string; reference: string; payment_id: string; ledger_transaction_id: string }
type BackendFinanceActivityBase = { id: string; type: 'finance'; status: 'completed' | 'pending' | 'failed'; title: string; summary: string; timestamp: string; reference: string; amount: string; currency: 'INR'; actor_user_id: string; actor_organization_id: string; event_status: string; sequence_number: number; detail: string | null }
export type BackendFinanceActivity = BackendFinanceActivityBase & (
  | { finance_record_type: 'payment_request'; payment_request_id: string; payment_id: string | null; budget_id: string | null; budget_name: string | null; budget_category: string | null; budget_period_start: string | null; budget_period_end: string | null; request_status: string; recipient_name: string; recipient_account: string }
  | { finance_record_type: 'budget'; payment_request_id: null; payment_id: null; budget_id: string; budget_name: string; budget_category: string | null; budget_period_start: string; budget_period_end: string; request_status: null; recipient_name: null; recipient_account: null }
)
export type BackendShipmentActivity = { id: string; type: 'shipment'; status: 'completed' | 'pending' | 'failed'; title: string; summary: string; timestamp: string; reference: string; shipment_id: string; shipment_status: string; event_status: string; sequence_number: number; actor_user_id: string; actor_organization_id: string; sender_organization_id: string; sender_name: string; sender_account_number: string; recipient_organization_id: string; recipient_name: string; recipient_account_number: string; product_id: string; product_name: string; sku: string; batch_id: string; batch_code: string; quantity: string; unit: string | null; source_location: string; destination_location: string; detail: string | null }
export type BackendInventoryActivity = { id: string; type: 'inventory'; status: 'completed'; title: string; summary: string; timestamp: string; reference: string; organization_id: string; product_id: string; sku: string; product_name: string; movement_type: 'stock_in' | 'stock_out' | 'movement' | 'adjustment'; quantity: string; unit: string | null; source_location: string | null; destination_location: string | null; adjustment_delta: string | null; reason: string | null; actor_user_id: string }
export type BackendAssetActivity = { id: string; type: 'asset'; status: 'completed'; title: string; summary: string; timestamp: string; reference: string; asset_id: string; asset_name: string; asset_identifier: string; event_type: string; sequence_number: number; actor_user_id: string; actor_organization_id: string; previous_state: Record<string, unknown> | null; resulting_state: Record<string, unknown>; metadata: Record<string, unknown> }
export type BackendBlockchainActivity = { id: string; type: 'blockchain'; status: 'completed' | 'pending' | 'failed'; title: string; summary: string; timestamp: string; reference: string; anchor_status: 'submitting' | 'submitted' | 'confirmed' | 'failed' | 'submission_failed' | 'simulated'; provider: string; network: string; digest: string; digest_version: string; asset_event_id: string | null; shipment_event_id: string | null; ledger_transaction_id: string | null; transaction_hash: string | null; block_number: number | null; confirmed_at: string | null }
export type BackendActivity = BackendPaymentActivity | BackendFinanceActivity | BackendInventoryActivity | BackendShipmentActivity | BackendAssetActivity | BackendBlockchainActivity
export type BackendPayment = { id: string; reference: string; recipient_name: string; recipient_account: string; amount: string; fee: string; total_debit: string; currency: 'INR'; purpose: import('./types').PaymentPurpose; note: string | null; status: 'pending' | 'processing' | 'completed'; created_at: string; completed_at: string | null }
export type BackendFinanceBudget = { id: string; organization_id: string; name: string; category: string | null; period_start: string; period_end: string; allocated_amount: string; spent_amount: string; committed_amount: string; remaining_amount: string; utilization_percent: string; currency: 'INR'; status: 'active' | 'closed'; created_at: string }
export type BackendPaymentRequest = { id: string; organization_id: string; requester_user_id: string; recipient_organization_id: string; recipient_account: string; recipient_name: string; budget_id: string | null; category: string | null; amount: string; currency: 'INR'; purpose: import('./types').PaymentPurpose; note: string | null; status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'PAYMENT_CREATED' | 'COMPLETED'; approver_user_id: string | null; approval_note: string | null; approved_at: string | null; payment_id: string | null; payment_reference: string | null; created_at: string; submitted_at: string | null; completed_at: string | null }
export type BackendPaymentRequestEvent = { id: string; payment_request_id: string; sequence_number: number; actor_user_id: string; from_status: BackendPaymentRequest['status'] | null; to_status: BackendPaymentRequest['status']; detail: string | null; created_at: string }
export type FinanceBudgetInput = { organization_id: string; name: string; category?: string; period_start: string; period_end: string; allocated_amount: string }
export type PaymentRequestInput = { organization_id: string; recipient_account: string; amount: string; purpose: import('./types').PaymentPurpose; note?: string; category?: string; budget_id?: string }
export type BackendProduct = { id: string; organization_id: string; sku: string; name: string; description: string | null; category: string; quantity: string | null; unit: string | null; status: 'active' | 'discontinued'; created_at: string; updated_at: string }
export type BackendInventoryStock = { id: string; organization_id: string; product_id: string; sku: string; product_name: string; unit: string | null; batch_id: string | null; batch_code: string | null; location: string; quantity: string; low_stock_threshold: string | null; is_low_stock: boolean; updated_at: string }
export type BackendInventoryMovement = { id: string; organization_id: string; product_id: string; sku: string; product_name: string; unit: string | null; batch_id: string | null; batch_code: string | null; actor_user_id: string; movement_type: 'stock_in' | 'stock_out' | 'movement' | 'adjustment'; source_location: string | null; destination_location: string | null; quantity: string; adjustment_delta: string | null; reason: string | null; source_quantity_before: string | null; source_quantity_after: string | null; destination_quantity_before: string | null; destination_quantity_after: string | null; created_at: string }
export type InventoryMovementRequest = { organization_id: string; product_id: string; batch_id?: string; movement_type: 'stock_in' | 'stock_out' | 'movement' | 'adjustment'; quantity: string; source_location?: string; destination_location?: string; adjustment_delta?: string; reason?: string; low_stock_threshold?: string }
export type BackendInventoryBatch = { id: string; organization_id: string; product_id: string; sku: string; product_name: string; unit: string | null; batch_code: string; manufactured_on: string | null; expires_on: string | null; notes: string | null; created_by_user_id: string; created_at: string }
export type InventoryBatchInput = { organization_id: string; product_id: string; batch_code: string; manufactured_on?: string; expires_on?: string; notes?: string }
export type BackendShipmentEvent = { id: string; sequence_number: number; actor_user_id: string; actor_organization_id: string; from_status: 'PREPARED' | 'DISPATCHED' | 'IN_TRANSIT' | 'RECEIVED' | 'REJECTED' | null; to_status: 'PREPARED' | 'DISPATCHED' | 'IN_TRANSIT' | 'RECEIVED' | 'REJECTED'; detail: string | null; created_at: string; blockchain_record: BackendBlockchainRecord | null }
export type BackendInventoryShipment = { id: string; sender_organization_id: string; sender_name: string; sender_account_number: string; recipient_organization_id: string; recipient_name: string; recipient_account_number: string; product_id: string; product_name: string; sku: string; unit: string | null; batch_id: string; batch_code: string; quantity: string; source_location: string; destination_location: string; status: 'PREPARED' | 'DISPATCHED' | 'IN_TRANSIT' | 'RECEIVED' | 'REJECTED'; note: string | null; rejection_reason: string | null; created_by_user_id: string; dispatcher_user_id: string | null; receiver_user_id: string | null; created_at: string; dispatched_at: string | null; in_transit_at: string | null; received_at: string | null; rejected_at: string | null; events: BackendShipmentEvent[] }
export type InventoryShipmentInput = { organization_id: string; recipient_account_number: string; product_id: string; batch_id: string; quantity: string; source_location: string; destination_location: string; note?: string }
export type BackendAsset = { id: string; organization_id: string; product_id: string | null; asset_identifier: string; category: string; name: string; description: string | null; metadata: Record<string, unknown>; current_owner_organization_id: string; current_custodian_organization_id: string | null; status: 'active' | 'retired'; created_at: string; updated_at: string }
export type BackendEvent = { id: string; asset_id: string; sequence_number: number; event_type: string; actor_user_id: string; actor_organization_id: string; previous_state: Record<string, unknown> | null; resulting_state: Record<string, unknown>; metadata: Record<string, unknown>; created_at: string }
export type BackendOwnership = { id: string; asset_id: string; organization_id: string; event_id: string; created_at: string }
export type BackendVerification = { asset_id: string; exists: true; current_owner_organization_id: string; current_custodian_organization_id: string | null; status: string; history_consistent: boolean; event_count: number; latest_anchor_record_event_id: string | null; blockchain_status: 'NOT_ANCHORED' | 'SIMULATED' | 'CONFIRMATION_PENDING' | 'ANCHORED_MATCH' | 'ANCHORED_MISMATCH'; integrity_warning: boolean }
export type BackendBlockchainStatus = { enabled: boolean; provider: string; network: string; chain_id: number | null; contract_address: string | null; contract_version: string | null; health: 'available' | 'simulated' | 'unavailable' | 'disabled' }
export type BackendBlockchainRecord = { id: string; ledger_transaction_id: string | null; asset_event_id: string | null; shipment_event_id: string | null; provider: string; network: string; chain_id: number | null; contract_address: string | null; contract_version: string | null; digest_version: string; digest: string; status: 'submitting' | 'submitted' | 'confirmed' | 'failed' | 'submission_failed' | 'simulated'; transaction_hash: string | null; block_number: number | null; submitted_at: string | null; confirmed_at: string | null; failure_code: string | null; created_at: string; updated_at: string }
export type BackendShipmentEventVerification = { shipment_id: string; shipment_event_id: string; exists: true; history_consistent: boolean; event_count: number; blockchain_status: 'NOT_ANCHORED' | 'SIMULATED' | 'CONFIRMATION_PENDING' | 'VERIFICATION_UNAVAILABLE' | 'ANCHORED_MATCH' | 'ANCHORED_MISMATCH'; integrity_warning: boolean; anchor_record: BackendBlockchainRecord | null }
export type { ErrorPayload }

export function profileFromBackend(user: BackendUser, account: BackendOrganization) {
  return { id: user.id, name: user.display_name || user.email, company: account.name, email: user.email, role: account.role, phone: user.phone ?? undefined, memberSince: user.created_at }
}
export function preferencesFromBackend(settings: BackendSettings, notifications: BackendNotifications) {
  return { timeZone: settings.time_zone, dateFormat: settings.date_format, showTechnicalByDefault: settings.show_technical_by_default, notifyPayments: notifications.transaction_notifications, notifySecurity: notifications.security_notifications, notifyProductUpdates: notifications.marketing_notifications, shareUsageData: settings.share_usage_data } as const
}
export function activityFromBackend(item: BackendActivity) {
  if (item.type === 'finance') {
    if (item.finance_record_type === 'budget') {
      return {
        id: item.id, reference: item.reference, kind: 'finance' as const, status: item.status, title: item.title, summary: item.summary,
        amount: { value: String(item.amount), currency: item.currency }, createdAt: item.timestamp, href: '/finance',
        details: [
          { label: 'Budget', value: item.budget_name, copyable: true },
          ...(item.budget_category ? [{ label: 'Category', value: item.budget_category }] : []),
          { label: 'Period', value: `${item.budget_period_start} – ${item.budget_period_end}` },
          { label: 'Lifecycle event', value: item.event_status.replaceAll('_', ' ') },
          { label: 'Allocated amount', value: exactMoney(item.amount) },
          { label: 'Actor user', value: item.actor_user_id, copyable: true },
          ...(item.detail ? [{ label: 'Detail', value: item.detail }] : []),
        ],
      }
    }
    return {
      id: item.id, reference: item.reference, kind: 'finance' as const, status: item.status, title: item.title, summary: item.summary,
      amount: { value: String(item.amount), currency: item.currency }, counterparty: item.recipient_name, createdAt: item.timestamp, href: '/finance',
      details: [
        { label: 'Payment request', value: item.payment_request_id, copyable: true },
        { label: 'Lifecycle event', value: `${item.event_status.replaceAll('_', ' ')} · step ${item.sequence_number}` },
        { label: 'Current request status', value: item.request_status.replaceAll('_', ' ') },
        ...(item.budget_id ? [{ label: 'Budget ID', value: item.budget_id, copyable: true }] : []),
        { label: 'Recipient account', value: item.recipient_account, copyable: true },
        { label: 'Amount', value: exactMoney(item.amount) },
        ...(item.payment_id ? [{ label: 'Payment ID', value: item.payment_id, copyable: true }] : []),
        { label: 'Actor user', value: item.actor_user_id, copyable: true },
        ...(item.detail ? [{ label: 'Transition detail', value: item.detail }] : []),
      ],
    }
  }
  if (item.type === 'shipment') {
    return {
      id: item.id, reference: item.reference, kind: 'shipment' as const, status: item.status, title: item.title, summary: item.summary,
      counterparty: `${item.sender_name} → ${item.recipient_name}`, createdAt: item.timestamp, href: '/inventory',
      details: [
        { label: 'Shipment', value: item.shipment_id, copyable: true },
        { label: 'Batch', value: `${item.batch_code} · ${item.product_name} · ${item.sku}` },
        { label: 'Quantity', value: `${item.quantity}${item.unit ? ` ${item.unit}` : ''}` },
        { label: 'Lifecycle event', value: `${item.event_status.replaceAll('_', ' ')} · step ${item.sequence_number}` },
        { label: 'Sender account', value: item.sender_account_number, copyable: true },
        { label: 'Recipient account', value: item.recipient_account_number, copyable: true },
        { label: 'Locations', value: `${item.source_location} → ${item.destination_location}` },
        { label: 'Actor user', value: item.actor_user_id, copyable: true },
        { label: 'Actor organization', value: item.actor_organization_id, copyable: true },
        ...(item.detail ? [{ label: 'Event detail', value: item.detail }] : []),
      ],
    }
  }
  if (item.type === 'inventory') {
    const locations = [item.source_location && `From ${item.source_location}`, item.destination_location && `To ${item.destination_location}`].filter((location): location is string => Boolean(location))
    return {
      id: item.id, reference: item.reference, kind: 'inventory' as const, status: 'completed' as const, title: item.title, summary: item.summary,
      createdAt: item.timestamp, href: '/inventory',
      details: [
        { label: 'Product', value: `${item.product_name} · ${item.sku}` },
        { label: 'Movement', value: item.movement_type.replaceAll('_', ' ') },
        { label: 'Quantity', value: `${item.adjustment_delta ?? item.quantity}${item.unit ? ` ${item.unit}` : ''}` },
        ...locations.map((location) => ({ label: 'Location', value: location })),
        ...(item.reason ? [{ label: 'Reason', value: item.reason }] : []),
        { label: 'Recorded by', value: item.actor_user_id, copyable: true },
        { label: 'Movement ID', value: item.id, copyable: true },
      ],
    }
  }
  if (item.type === 'asset') {
    const destinationAccount = item.metadata.recipient_account_number ?? item.metadata.custodian_account_number
    const previousOwner = item.previous_state?.owner
    const resultingOwner = item.resulting_state.owner
    const previousCustodian = item.previous_state?.custodian
    const resultingCustodian = item.resulting_state.custodian
    return {
      id: item.id, reference: item.reference, kind: 'asset' as const, status: 'completed' as const, title: item.title, summary: item.summary,
      createdAt: item.timestamp, href: `/assets/${encodeURIComponent(item.asset_id)}`,
      details: [
        { label: 'Asset', value: `${item.asset_name} · ${item.asset_identifier}` },
        { label: 'Event', value: item.event_type.replaceAll('_', ' ') },
        { label: 'Sequence', value: String(item.sequence_number) },
        ...(typeof previousOwner === 'string' ? [{ label: 'Previous owner organization', value: previousOwner, copyable: true }] : []),
        ...(typeof resultingOwner === 'string' ? [{ label: 'Resulting owner organization', value: resultingOwner, copyable: true }] : []),
        ...(typeof previousCustodian === 'string' ? [{ label: 'Previous custodian organization', value: previousCustodian, copyable: true }] : []),
        ...(typeof resultingCustodian === 'string' ? [{ label: 'Resulting custodian organization', value: resultingCustodian, copyable: true }] : []),
        ...(typeof destinationAccount === 'string' ? [{ label: item.event_type === 'TRANSFERRED' ? 'Recipient account number' : 'Custodian account number', value: destinationAccount, copyable: true }] : []),
        { label: 'Actor user', value: item.actor_user_id, copyable: true },
        { label: 'Actor organization', value: item.actor_organization_id, copyable: true },
        { label: 'Asset event ID', value: item.id, copyable: true },
      ],
    }
  }
  if (item.type === 'blockchain') {
    return {
      id: item.id, reference: item.reference, kind: 'blockchain' as const, status: item.status, title: item.title, summary: item.summary,
      createdAt: item.timestamp, href: item.shipment_event_id ? '/inventory' : item.asset_event_id ? '/assets' : '/finance',
      details: [
        { label: 'Anchor status', value: item.anchor_status === 'simulated' ? 'SIMULATED / DEVELOPMENT' : item.anchor_status.replaceAll('_', ' ') },
        { label: 'Provider', value: item.provider },
        { label: 'Network', value: item.network },
        { label: 'Digest version', value: item.digest_version },
        { label: 'Digest', value: item.digest, copyable: true },
        ...(item.asset_event_id ? [{ label: 'Asset event ID', value: item.asset_event_id, copyable: true }] : []),
        ...(item.shipment_event_id ? [{ label: 'Shipment event ID', value: item.shipment_event_id, copyable: true }] : []),
        ...(item.ledger_transaction_id ? [{ label: 'Ledger transaction ID', value: item.ledger_transaction_id, copyable: true }] : []),
        ...(item.transaction_hash ? [{ label: 'Transaction hash', value: item.transaction_hash, copyable: true }] : []),
        ...(item.block_number !== null ? [{ label: 'Block number', value: String(item.block_number) }] : []),
        ...(item.confirmed_at ? [{ label: 'Confirmed at', value: item.confirmed_at }] : []),
      ],
    }
  }
  return {
    id: item.id, reference: item.reference, kind: 'payment' as const, status: 'completed' as const, title: item.title, summary: item.summary,
    amount: { value: String(item.amount), currency: 'INR' as const }, counterparty: item.counterparty, createdAt: item.timestamp,
    details: [
      { label: 'Amount', value: exactMoney(item.amount) }, { label: 'Counterparty', value: item.counterparty },
      { label: 'Counterparty account', value: item.counterparty_account }, { label: 'Payment ID', value: item.payment_id, copyable: true },
      { label: 'Ledger transaction ID', value: item.ledger_transaction_id, copyable: true },
    ],
  }
}
export function paymentFromBackend(payment: BackendPayment) {
  const amount = String(payment.amount)
  return {
    id: payment.id, reference: payment.reference, kind: 'payment' as const, status: payment.status === 'completed' ? 'completed' as const : 'pending' as const,
    title: payment.status === 'completed' ? 'Payment completed' : 'Payment processing',
    summary: `${exactMoney(amount)} to ${payment.recipient_name} was recorded as an internal account transfer. Blockchain anchoring is separate and is not implied.`,
    amount: { value: amount, currency: payment.currency }, counterparty: payment.recipient_name, createdAt: payment.completed_at ?? payment.created_at,
    details: [
      { label: 'Amount', value: exactMoney(amount) }, { label: 'Recipient', value: payment.recipient_name },
      { label: 'Recipient account', value: payment.recipient_account }, { label: 'Purpose', value: payment.purpose },
      ...(payment.note ? [{ label: 'Note', value: payment.note }] : []), { label: 'Reference ID', value: payment.reference, copyable: true },
      { label: 'Payment ID', value: payment.id, copyable: true },
    ],
  }
}
export function verificationDescription(status: BackendVerification['blockchain_status']) {
  if (status === 'ANCHORED_MATCH') return 'Blockchain digest matches the recorded asset event.'
  if (status === 'SIMULATED') return 'The development provider recorded a simulated anchor. No public-chain transaction or confirmation exists.'
  if (status === 'ANCHORED_MISMATCH') return 'Blockchain digest mismatch. Treat this as an integrity warning.'
  if (status === 'CONFIRMATION_PENDING') return 'Blockchain anchor is awaiting confirmation.'
  return 'No blockchain anchor has been verified for this asset event.'
}
export function backendSettingsPayload(prefs: import('./types').AccountPreferences) {
  return { time_zone: prefs.timeZone, locale: 'en-IN', date_format: prefs.dateFormat, show_technical_by_default: prefs.showTechnicalByDefault, share_usage_data: prefs.shareUsageData }
}
export function backendNotificationPayload(prefs: import('./types').AccountPreferences) {
  return { transaction_notifications: prefs.notifyPayments, security_notifications: prefs.notifySecurity, marketing_notifications: prefs.notifyProductUpdates }
}
export function exactBalanceAfter(balance: string, amount: string) {
  const remaining = amountMinorUnits(balance) - amountMinorUnits(amount)
  return `${remaining / 100n}.${(remaining % 100n).toString().padStart(2, '0')}`
}
export function amountFitsBalance(amount: string, balance: string) { return amountMinorUnits(amount) <= amountMinorUnits(balance) }
export type SignupResult = {
  user: Pick<BackendUser, 'id' | 'email' | 'account_status' | 'email_verified' | 'created_at' | 'updated_at'>
  development_token?: string
}
export type ResendResult = { message: string; development_token?: string }
export type ProductCreateRequest = { organization_id: string; sku: string; name: string; description?: string; category: string; quantity?: string; unit?: string }
export type AssetCreateRequest = { organization_id: string; product_id?: string; asset_identifier: string; category: string; name: string; description?: string; metadata?: Record<string, unknown> }
export function serverApiBase() { return process.env.LEDGERCHAIN_API_URL?.trim().replace(/\/+$/, '') || 'http://127.0.0.1:8000' }
