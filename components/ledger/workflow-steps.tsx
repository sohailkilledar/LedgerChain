import { CheckIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Horizontal step indicator shared by every LedgerChain workflow. */
export function WorkflowSteps({
  steps,
  current,
  className,
}: {
  steps: string[]
  current: number
  className?: string
}) {
  return (
    <nav aria-label="Progress" className={className}>
      <p className="text-sm text-muted-foreground sm:hidden">
        Step {current + 1} of {steps.length}
        <span className="text-foreground">{` · ${steps[current]}`}</span>
      </p>
      <ol className="hidden items-center gap-3 sm:flex">
        {steps.map((step, index) => {
          const state = index < current ? 'done' : index === current ? 'current' : 'upcoming'
          return (
            <li key={step} className="flex items-center gap-3" aria-current={state === 'current' ? 'step' : undefined}>
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex size-6 items-center justify-center rounded-full border text-xs font-semibold',
                    state === 'done' && 'border-primary bg-primary text-primary-foreground',
                    state === 'current' && 'border-primary text-primary',
                    state === 'upcoming' && 'text-muted-foreground',
                  )}
                >
                  {state === 'done' ? <CheckIcon className="size-3.5" aria-hidden="true" /> : index + 1}
                </span>
                <span
                  className={cn(
                    'text-sm',
                    state === 'upcoming' ? 'text-muted-foreground' : 'font-medium',
                  )}
                >
                  {step}
                  {state === 'done' && <span className="sr-only"> (completed)</span>}
                </span>
              </span>
              {index < steps.length - 1 && (
                <span aria-hidden="true" className={cn('h-px w-8 lg:w-12', index < current ? 'bg-primary' : 'bg-border')} />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
