import { CheckIcon } from 'lucide-react'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

export interface ProgressStage<T extends string = string> {
  id: T
  label: string
  description: string
}

/**
 * Vertical status timeline for asynchronous ledger actions.
 * Shows what has happened, what is happening now, and what comes next.
 */
export function TransactionProgress<T extends string>({
  stages,
  current,
  className,
}: {
  stages: ProgressStage<T>[]
  current: T
  className?: string
}) {
  const currentIndex = stages.findIndex((stage) => stage.id === current)
  const active = stages[currentIndex]

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <p className="sr-only" role="status" aria-live="polite">
        {active ? `${active.label}. ${active.description}` : ''}
      </p>
      <ol className="flex flex-col">
        {stages.map((stage, index) => {
          const state = index < currentIndex ? 'done' : index === currentIndex ? 'current' : 'upcoming'
          const isLast = index === stages.length - 1
          const isFinalDone = isLast && state === 'current'
          return (
            <li key={stage.id} className="relative flex gap-4 pb-6 last:pb-0">
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={cn(
                    'absolute top-8 left-[0.9375rem] h-[calc(100%-2rem)] w-px',
                    state === 'done' ? 'bg-success' : 'bg-border',
                  )}
                />
              )}
              <span
                className={cn(
                  'relative flex size-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                  (state === 'done' || isFinalDone) && 'border-success bg-success text-primary-foreground',
                  state === 'current' && !isFinalDone && 'border-primary bg-info-soft text-primary',
                  state === 'upcoming' && 'bg-card text-muted-foreground',
                )}
              >
                {state === 'done' || isFinalDone ? (
                  <CheckIcon className="size-4" aria-hidden="true" />
                ) : state === 'current' ? (
                  <Spinner className="size-4" aria-hidden="true" role={undefined} aria-label={undefined} />
                ) : (
                  index + 1
                )}
              </span>
              <div className="flex flex-col gap-0.5 pt-1">
                <p
                  className={cn(
                    'text-sm font-medium',
                    state === 'upcoming' && 'text-muted-foreground',
                  )}
                >
                  {stage.label}
                  <span className="sr-only">
                    {state === 'done' || isFinalDone ? ' (done)' : state === 'current' ? ' (in progress)' : ' (not started)'}
                  </span>
                </p>
                <p className="text-sm text-muted-foreground text-pretty">{stage.description}</p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
