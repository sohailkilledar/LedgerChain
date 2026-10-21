'use client'

import { useEffect, useRef, useState } from 'react'
import { WorkflowSteps } from '@/components/ledger/workflow-steps'
import { ledgerService, newIdempotencyKey } from '@/lib/ledger/service'
import { LedgerError, type ActivityRecord, type LedgerErrorShape, type PaymentDraft, type PaymentStage } from '@/lib/ledger/types'
import { PaymentDetailsForm } from './payment-details-form'
import { PaymentProcessing } from './payment-processing'
import { PaymentFailure, PaymentSuccess } from './payment-result'
import { PaymentReview } from './payment-review'

type FlowState =
  | { step: 'details'; draft?: PaymentDraft }
  | { step: 'review'; draft: PaymentDraft }
  | { step: 'processing'; draft: PaymentDraft; stage: PaymentStage }
  | { step: 'success'; draft: PaymentDraft; record: ActivityRecord }
  | { step: 'failure'; draft: PaymentDraft; error: LedgerErrorShape }

const STEPS = ['Details', 'Review', 'Send', 'Done']
const stepIndex: Record<FlowState['step'], number> = {
  details: 0,
  review: 1,
  processing: 2,
  success: 3,
  failure: 2,
}

const unknownError: LedgerErrorShape = {
  code: 'UNKNOWN',
  message: 'We could not confirm the payment outcome. Check activity before starting another payment.',
  retryable: true,
  committed: false,
  outcomeUnknown: true,
}

export function PaymentFlow({ availableBalance }: { availableBalance: string }) {
  const [state, setState] = useState<FlowState>({ step: 'details' })
  const idempotencyKeyRef = useRef<string | undefined>(undefined)
  const headingRef = useRef<HTMLDivElement>(null)
  const hasMounted = useRef(false)

  // Move focus to the new step so keyboard and screen reader users follow the flow.
  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true
      return
    }
    headingRef.current?.focus()
  }, [state.step])

  async function submit(draft: PaymentDraft) {
    setState({ step: 'processing', draft, stage: 'submitted' })
    const idempotencyKey = idempotencyKeyRef.current ?? newIdempotencyKey()
    idempotencyKeyRef.current = idempotencyKey
    try {
      const record = await ledgerService.submitPayment(draft, {
        idempotencyKey,
        onStage: (stage) => setState({ step: 'processing', draft, stage }),
      })
      setState({ step: 'success', draft, record })
    } catch (error) {
      setState({ step: 'failure', draft, error: error instanceof LedgerError ? error : unknownError })
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <WorkflowSteps steps={STEPS} current={stepIndex[state.step]} />
      <div ref={headingRef} tabIndex={-1} className="outline-none">
        {state.step === 'details' && (
          <PaymentDetailsForm
            initial={state.draft}
            availableBalance={availableBalance}
            onContinue={(draft) => setState({ step: 'review', draft })}
          />
        )}
        {state.step === 'review' && (
          <PaymentReview
            draft={state.draft}
            availableBalance={availableBalance}
            onBack={() => {
              idempotencyKeyRef.current = undefined
              setState({ step: 'details', draft: state.draft })
            }}
            onConfirm={() => submit(state.draft)}
          />
        )}
        {state.step === 'processing' && <PaymentProcessing draft={state.draft} stage={state.stage} />}
        {state.step === 'success' && (
          <PaymentSuccess
            record={state.record}
            onNew={() => {
              idempotencyKeyRef.current = undefined
              setState({ step: 'details' })
            }}
          />
        )}
        {state.step === 'failure' && (
          <PaymentFailure
            error={state.error}
            onRetry={() => submit(state.draft)}
            onEdit={() => {
              idempotencyKeyRef.current = undefined
              setState({ step: 'details', draft: state.draft })
            }}
          />
        )}
      </div>
    </div>
  )
}
