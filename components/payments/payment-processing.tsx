import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { TransactionProgress, type ProgressStage } from '@/components/ledger/transaction-progress'
import { exactMoney } from '@/lib/ledger/api-client'
import type { PaymentDraft, PaymentStage } from '@/lib/ledger/types'

export const paymentStages: ProgressStage<PaymentStage>[] = [
  { id: 'submitted', label: 'Request received', description: 'We have your payment request and are checking the details.' },
  { id: 'recording', label: 'Recording your payment', description: 'Adding the payment to the secure ledger so it has a permanent record.' },
  { id: 'confirming', label: 'Confirming', description: 'Waiting for the network to verify the record. This usually takes under a minute.' },
  { id: 'completed', label: 'Payment complete', description: 'The money has been sent and the record is final.' },
]

export function PaymentProcessing({ draft, stage }: { draft: PaymentDraft; stage: PaymentStage }) {
  return (
    <Card aria-busy={stage !== 'completed'}>
      <CardHeader>
        <CardTitle>
          Sending {exactMoney(draft.amount)} to account {draft.recipientAccount}
        </CardTitle>
        <CardDescription>
          {"The backend is processing an internal LedgerChain account transfer. This is not an external bank settlement."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <TransactionProgress stages={paymentStages} current={stage} />
      </CardContent>
    </Card>
  )
}
