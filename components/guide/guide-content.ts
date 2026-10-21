import {
  BadgeCheckIcon,
  BoxIcon,
  CircleCheckIcon,
  ClipboardCheckIcon,
  FilePenLineIcon,
  FileTextIcon,
  HistoryIcon,
  LandmarkIcon,
  ListIcon,
  MousePointerClickIcon,
  ScanSearchIcon,
  SendIcon,
  ShieldCheckIcon,
  TruckIcon,
  UserRoundCheckIcon,
} from 'lucide-react'
import type { FaqItem } from './faq-list'
import type { FlowStep } from './flow-diagram'

export const whyFlow: FlowStep[] = [
  { icon: MousePointerClickIcon, title: 'Action' },
  { icon: ClipboardCheckIcon, title: 'Validation' },
  { icon: FileTextIcon, title: 'Database record' },
  { icon: CircleCheckIcon, title: 'Optional digest anchor' },
  { icon: HistoryIcon, title: 'Reported verification' },
]

export const howFlow: FlowStep[] = [
  { icon: MousePointerClickIcon, title: 'You submit an action', description: 'For example, create an internal payment or register an individual asset.' },
  { icon: ClipboardCheckIcon, title: 'The API validates it', description: 'Authentication, authorization, input rules, and domain constraints are checked.' },
  { icon: FilePenLineIcon, title: 'The database commits it', description: 'Payments update balances and double-entry ledger records in one transaction; asset changes append provenance events.' },
  { icon: CircleCheckIcon, title: 'The app returns a record', description: 'The response includes backend-generated IDs and the resulting status.' },
  { icon: ScanSearchIcon, title: 'Verification is reported', description: 'Application history consistency and any optional blockchain digest anchor are checked separately.' },
]

export const financeFlow: FlowStep[] = [
  { icon: SendIcon, title: 'Choose an account', description: 'Enter a LedgerChain organization account number and an INR amount.' },
  { icon: ClipboardCheckIcon, title: 'Validate details', description: 'The backend checks the recipient, available balance, and idempotency key.' },
  { icon: FilePenLineIcon, title: 'Commit transfer', description: 'Balance changes and double-entry ledger posting commit atomically.' },
  { icon: CircleCheckIcon, title: 'Return backend status', description: 'The payment response is authoritative; it represents an internal account transfer, not a bank settlement.' },
  { icon: ListIcon, title: 'View activity', description: 'Find the backend payment and ledger references in Activity.' },
]

export const supplyFlow: FlowStep[] = [
  { icon: BoxIcon, title: 'Product catalogued', description: 'Create an organization-scoped product record with a SKU and category.' },
  { icon: TruckIcon, title: 'Asset registered', description: 'Register an individual asset and optionally link it to a product.' },
  { icon: FilePenLineIcon, title: 'Asset event recorded', description: 'Ownership, custody, and retirement changes append provenance events.' },
  { icon: HistoryIcon, title: 'History inspected', description: 'Authorized users can review returned ownership and event history.' },
  { icon: BadgeCheckIcon, title: 'Verification reported', description: 'The backend checks history consistency and reports blockchain anchor state separately.' },
]

export const assetFlow: FlowStep[] = [
  { icon: LandmarkIcon, title: 'Asset registered', description: 'The current organization becomes the initial owner.' },
  { icon: UserRoundCheckIcon, title: 'Ownership or custody changes', description: 'Authorized owners can record a transfer or custodian change.' },
  { icon: HistoryIcon, title: 'Provenance event appended', description: 'The prior and resulting state are retained in the event history.' },
  { icon: ShieldCheckIcon, title: 'Verification reported', description: 'Internal consistency and any selected blockchain digest anchor are reported as distinct results.' },
]

export const glossary: { term: string; meaning: string }[] = [
  { term: 'Financial ledger', meaning: 'Double-entry debit and credit rows posted with a completed internal payment. Organization balances remain the operational source of truth.' },
  { term: 'Provenance event', meaning: 'An append-only asset lifecycle record describing a registration, transfer, custody change, or retirement.' },
  { term: 'Verification', meaning: 'A backend check of record existence, event-history consistency, and—when one exists—blockchain digest status.' },
  { term: 'Blockchain anchor', meaning: 'An optional digest/reference record. Development-provider results are explicitly simulated and do not have a real transaction hash or block number.' },
  { term: 'Confirmation', meaning: 'A mined-block depth reported by the configured EVM provider. It is not shown for simulated development anchors.' },
  { term: 'Transaction hash', meaning: 'An EVM transaction identifier returned only when a real blockchain transaction is submitted and mined.' },
  { term: 'Smart contract', meaning: 'The configured registry can store an authorized digest and reference; it does not validate whether source information is truthful.' },
]

export const faqs: FaqItem[] = [
  {
    question: 'What is LedgerChain?',
    answer:
      'LedgerChain records internal account transfers, product catalog entries, and individual asset provenance. Product movement tracking and external bank settlement are not provided by the current backend.',
  },
  {
    question: 'Why does LedgerChain use blockchain?',
    answer:
      'Selected record digests can be anchored through the configured provider. An anchor proves a digest/reference was recorded; it does not prove the source information was true or that a payment settled externally.',
  },
  {
    question: 'Do I need to understand blockchain to use LedgerChain?',
    answer:
      'No. The app shows payment status and backend references in plain language. Asset pages separately report application history consistency and blockchain anchor state.',
  },
  {
    question: 'Can I verify an asset?',
    answer:
      'Open an asset detail page to see whether its history is internally consistent and whether the backend reports an optional blockchain digest as pending, matching, or mismatched. This does not establish that source information was true.',
  },
  {
    question: 'What happens if a transaction fails?',
    answer:
      'Backend errors report whether a change committed when known. If the network response is lost during a payment, the outcome can be unknown; retrying the same payment uses its idempotency key.',
  },
  {
    question: 'What information is recorded?',
    answer:
      'Payments return the amount, participating accounts, reference, and backend-generated IDs. Asset provenance events retain state transitions. Neither record type by itself proves real-world truth.',
  },
  {
    question: 'What is an EVM transaction hash?',
    answer:
      'An identifier returned by an EVM transaction. It is distinct from the application record ID and the digest stored by the anchor registry, and exists only for real chain transactions.',
  },
]
