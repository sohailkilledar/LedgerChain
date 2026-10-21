/**
 * Frontend view models for LedgerChain.
 * These describe what the UI needs. The API layer (lib/ledger/service.ts)
 * is responsible for mapping backend / on-chain responses into these shapes.
 */

export type ActivityKind = 'payment' | 'finance' | 'loan' | 'product' | 'asset' | 'inventory' | 'shipment' | 'blockchain'

export type RecordStatus = 'completed' | 'pending' | 'failed' | 'action_required'

export interface Money {
  value: number | string
  currency: 'INR'
}

/** Level 2 – useful, human-readable details. */
export interface DetailField {
  label: string
  value: string
  /** Render in a monospace face with a copy button (e.g. reference IDs). */
  copyable?: boolean
}

/** Level 3 – the underlying ledger record, for advanced users. */
export interface TechnicalDetails {
  transactionHash: string
  blockNumber: number
  contractAddress: string
  network: string
  gasUsed: number
  confirmations: number
  timestamp: string
}

export interface ActivityRecord {
  id: string
  reference: string
  kind: ActivityKind
  status: RecordStatus
  /** Level 1 – short outcome, e.g. "Payment completed". */
  title: string
  /** Level 1 – one plain-language sentence explaining the outcome. */
  summary: string
  amount?: Money
  counterparty?: string
  createdAt: string
  href?: string
  details: DetailField[]
  technical?: TechnicalDetails
}

export type PaymentPurpose = 'invoice' | 'supplier' | 'salary' | 'personal' | 'other'

export interface PaymentDraft {
  recipientAccount: string
  amount: string
  purpose: PaymentPurpose
  note?: string
}

export type PaymentStage = 'submitted' | 'recording' | 'confirming' | 'completed'

/* ---------- Account ---------- */

export interface AccountProfile {
  id: string
  name: string
  company: string
  email: string
  role: string
  phone?: string
  memberSince: string
}

export type ProfileUpdate = Pick<AccountProfile, 'name' | 'company' | 'email' | 'phone'>

export type SupportTopic = 'payments' | 'records' | 'account' | 'other'

export interface SupportRequestInput {
  topic: SupportTopic
  email: string
  message: string
}

export interface AccountPreferences {
  timeZone: string
  dateFormat: 'dmy' | 'mdy' | 'iso'
  showTechnicalByDefault: boolean
  notifyPayments: boolean
  notifySecurity: boolean
  notifyProductUpdates: boolean
  shareUsageData: boolean
}

export type NotificationCategory = 'payments' | 'security' | 'account' | 'updates'

export interface AppNotification {
  id: string
  category: NotificationCategory
  title: string
  body: string
  createdAt: string
  read: boolean
  /** Where selecting the notification takes the user. */
  href?: string
}

export interface SessionDevice {
  id: string
  device: string
  browser: string
  location: string
  lastActiveAt: string
  current: boolean
}

export interface SecurityEvent {
  id: string
  title: string
  detail: string
  createdAt: string
  tone: 'neutral' | 'warning'
}

export interface SecurityOverview {
  passwordUpdatedAt: string
  twoFactorEnabled: boolean
  sessions: SessionDevice[]
  events: SecurityEvent[]
}

/* ---------- Authentication (prototype only) ---------- */

export interface SignInInput {
  email: string
  password: string
  remember: boolean
}

export interface SignUpInput {
  email: string
  password: string
}

export interface LedgerErrorShape {
  code: string
  /** Plain-language explanation shown to every user. */
  message: string
  /** Whether the same request can safely be retried. */
  retryable: boolean
  /** Whether any funds or data were committed before the failure. */
  committed: boolean
  /** True when a mutation may have reached the backend but no response was received. */
  outcomeUnknown?: boolean
  /** Raw detail for advanced users / support. */
  technicalMessage?: string
}

export class LedgerError extends Error implements LedgerErrorShape {
  code: string
  retryable: boolean
  committed: boolean
  outcomeUnknown?: boolean
  technicalMessage?: string

  constructor(shape: LedgerErrorShape) {
    super(shape.message)
    this.name = 'LedgerError'
    this.code = shape.code
    this.retryable = shape.retryable
    this.committed = shape.committed
    this.outcomeUnknown = shape.outcomeUnknown
    this.technicalMessage = shape.technicalMessage
  }
}
