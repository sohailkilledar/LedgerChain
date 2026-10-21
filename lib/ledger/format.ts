import { exactMoney } from './api-client'
import type { ActivityKind, Money, PaymentPurpose, RecordStatus } from './types'

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
})

const dateFormatter = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'Asia/Kolkata',
})

const dateTimeFormatter = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'Asia/Kolkata',
})

export function formatMoney(money: Money | number | string) {
  const value = typeof money === 'object' ? money.value : money
  return typeof value === 'number' ? currencyFormatter.format(value) : exactMoney(value)
}

export function formatDate(iso: string) {
  return dateFormatter.format(new Date(iso))
}

export function formatDateTime(iso: string) {
  return dateTimeFormatter.format(new Date(iso))
}

const relativeFormatter = new Intl.RelativeTimeFormat('en-IN', { numeric: 'auto' })

/** "5 minutes ago", "yesterday", or a full date once older than a week. */
export function formatRelative(iso: string, now: Date = new Date()) {
  const seconds = Math.round((new Date(iso).getTime() - now.getTime()) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'Just now'
  if (abs < 3600) return relativeFormatter.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return relativeFormatter.format(Math.round(seconds / 3600), 'hour')
  if (abs < 604800) return relativeFormatter.format(Math.round(seconds / 86400), 'day')
  return formatDate(iso)
}

export function shortenHash(hash: string, size = 6) {
  if (hash.length <= size * 2 + 2) return hash
  return `${hash.slice(0, size + 2)}…${hash.slice(-size)}`
}

export const kindLabels: Record<ActivityKind, string> = {
  payment: 'Payment',
  finance: 'Finance',
  loan: 'Loan',
  product: 'Product',
  asset: 'Asset',
  inventory: 'Inventory',
  shipment: 'Shipment',
  blockchain: 'Blockchain evidence',
}

export const statusLabels: Record<RecordStatus, string> = {
  completed: 'Completed',
  pending: 'In progress',
  failed: 'Failed',
  action_required: 'Needs your action',
}

export const purposeLabels: Record<PaymentPurpose, string> = {
  invoice: 'Invoice payment',
  supplier: 'Supplier payment',
  salary: 'Salary or wages',
  personal: 'Personal transfer',
  other: 'Other',
}
