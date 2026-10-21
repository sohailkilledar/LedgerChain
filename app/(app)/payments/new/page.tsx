import type { Metadata } from 'next'
import { PageHeader } from '@/components/ledger/page-header'
import { PaymentAside } from '@/components/payments/payment-aside'
import { PaymentFlow } from '@/components/payments/payment-flow'
import { getServerAccount } from '@/lib/ledger/server-service'

export const metadata: Metadata = {
  title: 'Send a payment',
}

export default async function NewPaymentPage() {
  const account = await getServerAccount()

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        title="Send a payment"
        description="Transfer INR between LedgerChain organization accounts. This is internal bookkeeping, not an external bank settlement."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Payments' }, { label: 'Send payment' }]}
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,42rem)_18rem] lg:gap-10">
        <PaymentFlow availableBalance={String(account.balance)} />
        <PaymentAside />
      </div>
    </div>
  )
}
